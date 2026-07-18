package ru.quantai.neskuchno.feature.character

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.quantai.neskuchno.core.AppResult
import ru.quantai.neskuchno.core.CharacterProfile
import ru.quantai.neskuchno.data.local.MessageEntity
import ru.quantai.neskuchno.data.preferences.AppPreferences
import ru.quantai.neskuchno.data.repository.AiRepository
import ru.quantai.neskuchno.data.repository.CharacterRepository
import ru.quantai.neskuchno.data.repository.TtsRepository
import ru.quantai.neskuchno.media.AudioPlaybackManager
import ru.quantai.neskuchno.ui.userMessage

sealed interface CharacterSendState {
    data object Idle : CharacterSendState
    data object Sending : CharacterSendState
    data class Error(val message: String, val canRetry: Boolean = true) : CharacterSendState
}

class CharacterViewModel(
    private val characterId: String,
    private val characters: CharacterRepository,
    private val ai: AiRepository,
    private val tts: TtsRepository,
    private val audio: AudioPlaybackManager,
    private val preferences: AppPreferences,
) : ViewModel() {
    val character: StateFlow<CharacterProfile?> = characters.observe(characterId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)
    val messages: StateFlow<List<MessageEntity>> = characters.observeMessages(characterId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    private val _input = MutableStateFlow("")
    val input: StateFlow<String> = _input.asStateFlow()
    private val _sendState = MutableStateFlow<CharacterSendState>(CharacterSendState.Idle)
    val sendState: StateFlow<CharacterSendState> = _sendState.asStateFlow()
    private var lastFailedText: String? = null

    fun setInput(value: String) { _input.value = value }

    fun send() {
        val text = _input.value.trim()
        if (text.isBlank() || _sendState.value == CharacterSendState.Sending) return
        _input.value = ""
        submit(text, addUserMessage = true)
    }

    fun retry() {
        val text = lastFailedText ?: return
        if (_sendState.value == CharacterSendState.Sending) return
        submit(text, addUserMessage = false)
    }

    private fun submit(text: String, addUserMessage: Boolean) {
        val profile = character.value ?: return
        viewModelScope.launch {
            if (addUserMessage) characters.addMessage(characterId, "user", text)
            _sendState.value = CharacterSendState.Sending
            val history = characters.history(characterId)
            val effective = if (profile.isDemo) {
                val selected = runCatching {
                    ru.quantai.neskuchno.core.ResponseLength.valueOf(preferences.responseLength.first())
                }.getOrDefault(profile.responseLength)
                profile.copy(responseLength = selected)
            } else profile
            val priorHistory = if (history.lastOrNull()?.first == "user" && history.lastOrNull()?.second == text) {
                history.dropLast(1)
            } else history
            when (val result = ai.chat(effective, priorHistory, text)) {
                is AppResult.Success -> {
                    characters.addMessage(characterId, "assistant", result.value)
                    lastFailedText = null
                    _sendState.value = CharacterSendState.Idle
                    if (preferences.autoSpeak.first()) speak(result.value, profile.voice)
                }
                is AppResult.Failure -> {
                    lastFailedText = text
                    _sendState.value = CharacterSendState.Error(result.error.userMessage())
                }
            }
        }
    }

    fun clear() = viewModelScope.launch {
        characters.clearChat(characterId)
        lastFailedText = null
        _sendState.value = CharacterSendState.Idle
    }

    fun repeatLast() {
        val text = messages.value.lastOrNull { it.role == "assistant" }?.text ?: return
        speak(text, character.value?.voice ?: "Zephyr")
    }

    private fun speak(text: String, voice: String) {
        viewModelScope.launch {
            when (val result = tts.synthesize(text, voice)) {
                is AppResult.Success -> audio.play(result.value)
                is AppResult.Failure -> _sendState.value = CharacterSendState.Error(result.error.userMessage(), canRetry = false)
            }
        }
    }

    class Factory(
        private val id: String,
        private val characters: CharacterRepository,
        private val ai: AiRepository,
        private val tts: TtsRepository,
        private val audio: AudioPlaybackManager,
        private val preferences: AppPreferences,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = CharacterViewModel(id, characters, ai, tts, audio, preferences) as T
    }
}
