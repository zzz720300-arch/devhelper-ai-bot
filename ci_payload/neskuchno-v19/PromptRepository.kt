package ru.quantai.neskuchno.data.repository

import android.content.Context
import ru.quantai.neskuchno.core.CharacterProfile
import ru.quantai.neskuchno.core.ResponseLength
import java.security.MessageDigest

class PromptRepository(private val context: Context) {
    fun readAsset(path: String): String = context.assets.open(path).bufferedReader().use { it.readText() }

    fun absurdNewsPrompt(): String = readAsset("prompts/absurd_news_system.txt")
    fun whatIfPrompt(): String = readAsset("prompts/what_if_system.txt")
    fun demoCorePrompt(): String = readAsset("prompts/demo_core_system.txt")
    fun demoRolePrompt(): String = readAsset("prompts/demo_role_prompt.txt")
    fun demoRuntimePrompt(): String = readAsset("prompts/demo_runtime_session.txt")

    fun roleVersion(prompt: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(prompt.toByteArray(Charsets.UTF_8))
        return digest.take(8).joinToString("") { "%02x".format(it) }
    }

    fun characterSystemPrompt(
        character: CharacterProfile,
        responseLength: ResponseLength,
        sessionId: String,
        mode: String = "conversation",
    ): String {
        val role = character.prompt.trim()
        require(role.length >= 500) { "Промпт персонажа повреждён или слишком короткий" }
        val runtime = demoRuntimePrompt()
            .replace("{{CHARACTER_NAME}}", character.name)
            .replace("{{LANGUAGE}}", "русский")
            .replace("{{USER_ADDRESS}}", "ты")
            .replace("{{USER_NAME}}", "не задано")
            .replace("{{NORMAL_SENTENCES}}", responseLength.maxSentences.toString())
            .replace("{{MAX_NORMAL_TOKENS}}", "700")
            .replace("{{MAX_LONG_TOKENS}}", "1200")
            .replace("{{LONG_FORM_ALLOWED}}", (responseLength == ResponseLength.DETAILED).toString())
            .replace("{{MODE}}", mode)
            .replace("{{ROLE_VERSION}}", roleVersion(role))
            .replace("{{SESSION_ID}}", sessionId)
        return buildString {
            appendLine("НЕИЗМЕНЯЕМОЕ ЯДРО")
            appendLine(demoCorePrompt().trim())
            appendLine()
            appendLine("АКТИВНЫЙ ПЕРСОНАЖ")
            appendLine(role)
            appendLine()
            appendLine(runtime.trim())
        }
    }
}
