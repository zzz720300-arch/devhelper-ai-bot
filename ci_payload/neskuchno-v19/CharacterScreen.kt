package ru.quantai.neskuchno.feature.character

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowBack
import androidx.compose.material.icons.rounded.ClearAll
import androidx.compose.material.icons.rounded.Replay
import androidx.compose.material.icons.rounded.Send
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ru.quantai.neskuchno.ui.components.ErrorBlock
import ru.quantai.neskuchno.ui.components.LoadingBlock
import ru.quantai.neskuchno.ui.components.LoopingVideoPlayer
import ru.quantai.neskuchno.ui.components.NeonBackground
import ru.quantai.neskuchno.ui.components.NeonPanel
import ru.quantai.neskuchno.ui.components.NeonTextField
import ru.quantai.neskuchno.ui.components.ScreenHeader
import ru.quantai.neskuchno.ui.components.VoiceInputButton
import ru.quantai.neskuchno.ui.theme.Cyan400
import ru.quantai.neskuchno.ui.theme.Navy950
import ru.quantai.neskuchno.ui.theme.TextPrimary
import ru.quantai.neskuchno.ui.theme.TextSecondary

private val ComposerReserve = 184.dp

@Composable
fun CharacterScreen(vm: CharacterViewModel, onBack: () -> Unit) {
    val character by vm.character.collectAsStateWithLifecycle()
    val messages by vm.messages.collectAsStateWithLifecycle()
    val input by vm.input.collectAsStateWithLifecycle()
    val sendState by vm.sendState.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

    LaunchedEffect(messages.size, sendState) {
        val extra = when (sendState) {
            CharacterSendState.Sending -> 1
            is CharacterSendState.Error -> 1
            else -> 0
        }
        val target = messages.size + extra - 1
        if (target >= 0) runCatching { listState.animateScrollToItem(target) }
    }

    NeonBackground {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .navigationBarsPadding(),
        ) {
            LoopingVideoPlayer(
                character?.videoUri,
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxHeight()
                    .padding(bottom = ComposerReserve),
                cropToFill = true,
                cornerRadius = 0.dp,
            )

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxHeight()
                    .padding(bottom = ComposerReserve)
                    .background(
                        Brush.verticalGradient(
                            0f to Navy950.copy(alpha = .74f),
                            .18f to Color.Transparent,
                            .58f to Color.Transparent,
                            1f to Navy950.copy(alpha = .88f),
                        )
                    )
            )

            Column(modifier = Modifier.fillMaxSize()) {
                ScreenHeader(
                    character?.name ?: "Персонаж",
                    character?.description,
                    onBack,
                    Icons.Rounded.ArrowBack,
                )
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp),
                    horizontalArrangement = Arrangement.End,
                ) {
                    IconButton(onClick = vm::repeatLast) {
                        Icon(Icons.Rounded.Replay, "Повторить ответ", tint = Cyan400)
                    }
                    IconButton(onClick = vm::clear) {
                        Icon(Icons.Rounded.ClearAll, "Очистить диалог", tint = Cyan400)
                    }
                }
                Spacer(Modifier.weight(1f))
            }

            LazyColumn(
                state = listState,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .padding(start = 12.dp, end = 12.dp, bottom = ComposerReserve + 8.dp)
                    .heightIn(max = 248.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(messages, key = { it.id }) { line ->
                    NeonPanel {
                        Text(
                            if (line.role == "user") "Вы" else character?.name ?: "Персонаж",
                            color = Cyan400,
                            style = MaterialTheme.typography.labelLarge,
                        )
                        Spacer(Modifier.size(4.dp))
                        Text(line.text, color = TextPrimary, style = MaterialTheme.typography.bodyLarge)
                    }
                }
                if (sendState == CharacterSendState.Sending) item { LoadingBlock("Персонаж отвечает…") }
                if (sendState is CharacterSendState.Error) {
                    val error = sendState as CharacterSendState.Error
                    item { ErrorBlock(error.message, onRetry = if (error.canRetry) vm::retry else null) }
                }
            }

            NeonPanel(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(start = 12.dp, end = 12.dp, bottom = 18.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    VoiceInputButton(onText = vm::setInput, size = 58)
                    NeonTextField(
                        value = input,
                        onValueChange = vm::setInput,
                        label = "Сообщение",
                        modifier = Modifier.weight(1f),
                        maxLines = 3,
                        trailing = {
                            IconButton(onClick = vm::send, enabled = input.isNotBlank()) {
                                Icon(
                                    Icons.Rounded.Send,
                                    "Отправить",
                                    tint = if (input.isNotBlank()) Cyan400 else TextSecondary,
                                )
                            }
                        },
                    )
                }
            }
        }
    }
}
