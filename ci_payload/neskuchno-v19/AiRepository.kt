package ru.quantai.neskuchno.data.repository

import com.google.gson.Gson
import retrofit2.HttpException
import ru.quantai.neskuchno.BuildConfig
import ru.quantai.neskuchno.core.AiGeneratedText
import ru.quantai.neskuchno.core.AppError
import ru.quantai.neskuchno.core.AppResult
import ru.quantai.neskuchno.core.CharacterProfile
import ru.quantai.neskuchno.core.ResponseLength
import ru.quantai.neskuchno.core.TextRules
import ru.quantai.neskuchno.data.network.ChatCompletionRequest
import ru.quantai.neskuchno.data.network.ChatMessageDto
import ru.quantai.neskuchno.data.network.GeneratedJsonDto
import ru.quantai.neskuchno.data.network.NetworkErrorMapper
import ru.quantai.neskuchno.data.network.ResponseFormatDto
import ru.quantai.neskuchno.data.network.RouterAiApi
import ru.quantai.neskuchno.data.security.RouterAiKeyProvider
import java.io.IOException
import java.util.UUID

class AiRepository(
    private val api: RouterAiApi,
    private val prompts: PromptRepository,
    private val keyProvider: RouterAiKeyProvider,
    private val gson: Gson = Gson(),
) {
    private fun authorization(): String? = keyProvider.get().takeIf { keyProvider.isConfigured() }?.let { "Bearer $it" }

    suspend fun generateAbsurdNews(topic: String, category: String, previous: AiGeneratedText?): AppResult<AiGeneratedText> {
        val auth = authorization() ?: return AppResult.Failure(AppError.Unauthorized)
        val previousBlock = previous?.let { "Нельзя повторять предыдущий вариант: ${it.title}. ${it.body}" }
            ?: "Предыдущего варианта нет."
        val user = buildString {
            appendLine("Категория: $category")
            appendLine("Тема: ${topic.ifBlank { "самостоятельно выбери новую случайную бытовую тему" }}")
            appendLine(previousBlock)
            appendLine("Идентификатор нового запроса: ${UUID.randomUUID()}")
            append("Создай новый самостоятельный вариант. Не используй заготовленный список.")
        }
        return generateJson(auth, prompts.absurdNewsPrompt(), user, maxSentences = 5, temperature = 1.05)
    }

    suspend fun generateWhatIf(question: String, style: String): AppResult<AiGeneratedText> {
        if (question.isBlank()) return AppResult.Failure(AppError.Validation("Введите ситуацию"))
        val auth = authorization() ?: return AppResult.Failure(AppError.Unauthorized)
        return generateJson(auth, prompts.whatIfPrompt(), "Стиль: $style. Вопрос: $question", 15, 0.9)
    }

    suspend fun chat(character: CharacterProfile, history: List<Pair<String, String>>, userText: String): AppResult<String> {
        if (userText.isBlank()) return AppResult.Failure(AppError.Validation("Введите сообщение"))
        val auth = authorization() ?: return AppResult.Failure(AppError.Unauthorized)
        val system = runCatching {
            prompts.characterSystemPrompt(character, character.responseLength, character.id)
        }.getOrElse { return AppResult.Failure(AppError.Validation(it.message ?: "Промпт персонажа повреждён")) }
        val messages = buildList {
            add(ChatMessageDto("system", system))
            history.takeLast(12).forEach { (role, content) -> add(ChatMessageDto(role, content)) }
            add(ChatMessageDto("user", userText))
        }
        return try {
            val maxTokens = if (character.responseLength == ResponseLength.DETAILED) 1_200 else 700
            val response = api.chat(
                auth,
                ChatCompletionRequest(BuildConfig.ROUTERAI_TEXT_MODEL, messages, 0.30, maxTokens),
            )
            if (!response.isSuccessful) return AppResult.Failure(mapHttp(response.code(), response.errorBody()?.string() ?: response.message()))
            val raw = response.body()?.choices?.firstOrNull()?.message?.content.orEmpty().trim()
            if (raw.isBlank()) AppResult.Failure(AppError.Remote(response.code(), "Пустой ответ модели"))
            else AppResult.Success(TextRules.limitSentences(raw, character.responseLength.maxSentences))
        } catch (e: IOException) {
            AppResult.Failure(NetworkErrorMapper.from(e))
        } catch (e: HttpException) {
            AppResult.Failure(mapHttp(e.code(), e.message()))
        } catch (e: Exception) {
            AppResult.Failure(AppError.Unexpected(e.message ?: "Неизвестная ошибка"))
        }
    }

    private suspend fun generateJson(auth: String, system: String, user: String, maxSentences: Int, temperature: Double): AppResult<AiGeneratedText> = try {
        val response = api.chat(
            auth,
            ChatCompletionRequest(
                model = BuildConfig.ROUTERAI_TEXT_MODEL,
                messages = listOf(ChatMessageDto("system", system), ChatMessageDto("user", user)),
                temperature = temperature,
                maxTokens = if (maxSentences <= 5) 420 else 900,
                responseFormat = ResponseFormatDto(),
            )
        )
        if (!response.isSuccessful) {
            AppResult.Failure(mapHttp(response.code(), response.errorBody()?.string() ?: response.message()))
        } else {
            val raw = response.body()?.choices?.firstOrNull()?.message?.content.orEmpty().trim()
            val parsed = runCatching { gson.fromJson(raw, GeneratedJsonDto::class.java) }.getOrNull()
            val title = parsed?.title?.trim().orEmpty()
            val body = TextRules.limitSentences(parsed?.body.orEmpty(), maxSentences)
            val disclaimer = parsed?.disclaimer?.trim().orEmpty()
            if (title.isBlank() || body.isBlank()) AppResult.Failure(AppError.Remote(response.code(), "Модель вернула некорректный JSON"))
            else AppResult.Success(AiGeneratedText(title, body, disclaimer))
        }
    } catch (e: IOException) {
        AppResult.Failure(NetworkErrorMapper.from(e))
    } catch (e: HttpException) {
        AppResult.Failure(mapHttp(e.code(), e.message()))
    } catch (e: Exception) {
        AppResult.Failure(AppError.Unexpected(e.message ?: "Неизвестная ошибка"))
    }

    private fun mapHttp(code: Int, message: String?): AppError = when (code) {
        401, 403 -> AppError.Unauthorized
        408, 504 -> AppError.Timeout
        429 -> AppError.RateLimited
        else -> AppError.Remote(code, message)
    }
}
