package ru.quantai.neskuchno.data.repository

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import ru.quantai.neskuchno.R
import ru.quantai.neskuchno.core.CharacterProfile
import ru.quantai.neskuchno.core.ResponseLength
import ru.quantai.neskuchno.data.local.CharacterDao
import ru.quantai.neskuchno.data.local.CharacterEntity
import ru.quantai.neskuchno.data.local.MessageDao
import ru.quantai.neskuchno.data.local.MessageEntity
import java.io.File
import java.util.UUID

class CharacterRepository(
    private val context: Context,
    private val characters: CharacterDao,
    private val messages: MessageDao,
    private val prompts: PromptRepository,
) {
    val all: Flow<List<CharacterProfile>> = characters.observeAll().map { list -> list.map(::toProfile) }
    fun observe(id: String): Flow<CharacterProfile?> = characters.observeById(id).map { it?.let(::toProfile) }
    fun observeMessages(id: String) = messages.observeForCharacter(id)

    suspend fun seedDemo() {
        val embeddedRole = prompts.demoRolePrompt().trim()
        require(embeddedRole.length >= 500) { "Встроенный промпт персонажа повреждён" }
        val existing = characters.getById(DEMO_ID)
        val needsRefresh = existing == null ||
            existing.prompt.trim() != embeddedRole ||
            existing.name != DEMO_NAME ||
            existing.voice != DEMO_VOICE
        if (!needsRefresh) return

        val video = Uri.parse("android.resource://${context.packageName}/${R.raw.demo_character}").toString()
        characters.insert(
            CharacterEntity(
                id = DEMO_ID,
                name = DEMO_NAME,
                description = "Живой голосовой персонаж с постоянной ролью",
                prompt = embeddedRole,
                videoUri = video,
                coverUri = null,
                voice = DEMO_VOICE,
                responseLength = ResponseLength.NORMAL.name,
                isDemo = true,
                createdAt = 0,
            )
        )
        if (existing != null) messages.clear(DEMO_ID)
    }

    suspend fun save(
        id: String? = null,
        name: String,
        description: String,
        prompt: String,
        videoSource: Uri?,
        voice: String,
        responseLength: ResponseLength,
    ): String {
        val characterId = id ?: UUID.randomUUID().toString()
        val dir = File(context.filesDir, "characters/$characterId").apply { mkdirs() }
        val copiedVideo = videoSource?.let { source ->
            val target = File(dir, "avatar.mp4")
            context.contentResolver.openInputStream(source)?.use { input -> target.outputStream().use { input.copyTo(it) } }
            target.toURI().toString()
        }
        val cleanPrompt = prompt.trim()
        require(cleanPrompt.length >= 100) { "Промпт персонажа слишком короткий" }
        characters.insert(
            CharacterEntity(
                id = characterId,
                name = name.trim(),
                description = description.trim(),
                prompt = cleanPrompt,
                videoUri = copiedVideo,
                coverUri = null,
                voice = voice,
                responseLength = responseLength.name,
                isDemo = false,
                createdAt = System.currentTimeMillis(),
            )
        )
        return characterId
    }

    suspend fun addMessage(characterId: String, role: String, text: String) = messages.insert(
        MessageEntity(characterId = characterId, role = role, text = text, createdAt = System.currentTimeMillis())
    )

    suspend fun history(characterId: String, limit: Int = 12): List<Pair<String, String>> =
        messages.latest(characterId, limit).reversed().map { it.role to it.text }

    suspend fun clearChat(characterId: String) = messages.clear(characterId)

    private fun toProfile(e: CharacterEntity) = CharacterProfile(
        id = e.id,
        name = e.name,
        description = e.description,
        prompt = e.prompt,
        videoUri = e.videoUri,
        coverUri = e.coverUri,
        voice = e.voice.ifBlank { DEMO_VOICE },
        responseLength = runCatching { ResponseLength.valueOf(e.responseLength) }.getOrDefault(ResponseLength.NORMAL),
        isDemo = e.isDemo,
    )

    companion object {
        const val DEMO_ID = "demo-character"
        const val DEMO_NAME = "Наташа"
        const val DEMO_VOICE = "Zephyr"
    }
}
