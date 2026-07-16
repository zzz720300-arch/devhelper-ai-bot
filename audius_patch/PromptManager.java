package ru.demo.voice;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.UUID;

final class PromptManager {
    static final class PromptBundle {
        final String systemPrompt;
        final String roleText;
        final String roleHash;

        PromptBundle(String systemPrompt, String roleText, String roleHash) {
            this.systemPrompt = systemPrompt;
            this.roleText = roleText;
            this.roleHash = roleHash;
        }
    }

    private final Context context;
    private final String core;
    private final String role;
    private final String runtimeTemplate;
    private final String apiKey;
    private final String sessionId = UUID.randomUUID().toString();

    PromptManager(Context context) throws IOException {
        this.context = context.getApplicationContext();
        core = readAsset("prompts/01_CORE_SYSTEM_PROMPT.txt");
        role = readAsset("prompts/default_role_prompt.txt");
        runtimeTemplate = readAsset("prompts/03_RUNTIME_SESSION_PROMPT.txt");
        apiKey = readAsset("config/routerai_key.txt").trim();
    }

    PromptBundle load() {
        String runtime = runtimeTemplate
                .replace("{{SESSION_ID}}", sessionId)
                .replace("{{DATE_TIME}}", new java.util.Date().toString());
        String system = "===== НЕИЗМЕНЯЕМОЕ ЯДРО =====\n"
                + core
                + "\n\n===== АКТИВНЫЙ ПЕРСОНАЖ =====\n"
                + role
                + "\n\n===== ПРАВИЛА ТЕКУЩЕГО СЕАНСА =====\n"
                + runtime
                + "\n\n===== ВОЗМОЖНОСТЬ МУЗЫКИ =====\n"
                + "Музыкальные команды выполняются приложением напрямую через Audius. "
                + "Не отказывайся от воспроизведения и не утверждай, что музыка недоступна.";
        return new PromptBundle(system, role, sha256(role));
    }

    String getApiKey() {
        return apiKey;
    }

    private String readAsset(String path) throws IOException {
        try (InputStream input = context.getAssets().open(path);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int read;
            while ((read = input.read(buffer)) >= 0) output.write(buffer, 0, read);
            return output.toString(StandardCharsets.UTF_8.name()).trim();
        }
    }

    private static String sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : hash) builder.append(String.format("%02x", b));
            return builder.toString();
        } catch (Exception e) {
            return Integer.toHexString(text.hashCode());
        }
    }
}
