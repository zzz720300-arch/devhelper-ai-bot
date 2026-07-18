#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])
ui = root / "app/src/main/java/ru/quantai/neskuchno/UiFactory.java"
main = root / "app/src/main/java/ru/quantai/neskuchno/MainActivity.java"
client = root / "app/src/main/java/ru/quantai/neskuchno/RouterAiClient.java"

ui_text = ui.read_text(encoding="utf-8")
ui_text = ui_text.replace("button.setTextAllCaps(false);", "button.setAllCaps(false);")
ui.write_text(ui_text, encoding="utf-8")

text = main.read_text(encoding="utf-8")
if "import android.os.Build;" not in text:
    text = text.replace("import android.os.Bundle;\n", "import android.os.Build;\nimport android.os.Bundle;\n")

text = text.replace(
    "        storyRepository = new StoryRepository(this);\n        showHome();\n",
    "        storyRepository = new StoryRepository(this);\n        showHome();\n        if (Build.VERSION.SDK_INT >= 33) Api33BackDispatcher.register(this);\n",
)

text = text.replace(
    "            getContentResolver().takePersistableUriPermission(uri,\n"
    "                    data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION));",
    "            getContentResolver().takePersistableUriPermission(\n"
    "                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);",
)

old_back = '''    @Override public void onBackPressed() {
        if (recorder.isRecording()) {
            recorder.cancel();
            Toast.makeText(this, "Запись отменена", Toast.LENGTH_SHORT).show();
            return;
        }
        if (backAction != null) backAction.run();
        else super.onBackPressed();
    }
'''
new_back = '''    @android.annotation.SuppressLint("GestureBackNavigation")
    @SuppressWarnings("deprecation")
    @Override public void onBackPressed() {
        handleBackNavigation();
    }

    private void handleBackNavigation() {
        if (recorder != null && recorder.isRecording()) {
            recorder.cancel();
            Toast.makeText(this, "Запись отменена", Toast.LENGTH_SHORT).show();
            return;
        }
        if (backAction != null) backAction.run();
        else finish();
    }

    @android.annotation.TargetApi(33)
    private static final class Api33BackDispatcher {
        static void register(MainActivity activity) {
            activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    activity::handleBackNavigation);
        }
    }
'''
if old_back in text:
    text = text.replace(old_back, new_back)
main.write_text(text, encoding="utf-8")

router = client.read_text(encoding="utf-8")
router = router.replace(
    'public static final String TTS_MODEL = "x-ai/grok-voice-tts-1.0";',
    'public static final String TTS_MODEL = "google/gemini-3.1-flash-tts-preview";',
)
router = router.replace(
    'public static final String TTS_VOICE = "eve";',
    'public static final String TTS_VOICE = "Zephyr";',
)
if "import java.nio.ByteBuffer;" not in router:
    router = router.replace(
        "import java.net.URL;\nimport java.nio.charset.StandardCharsets;",
        "import java.net.URL;\nimport java.nio.ByteBuffer;\nimport java.nio.ByteOrder;\nimport java.nio.charset.StandardCharsets;",
    )

method_start = router.index("    public File synthesize(String text) throws IOException, JSONException {")
method_end = router.index("    public String transcribe(File wav)", method_start)
new_tts = '''    public File synthesize(String text) throws IOException, JSONException {
        ensureKey();
        String clean = text == null ? "" : text.replaceAll("https?://\\\\S+", "").trim();
        if (clean.isEmpty()) throw new IOException("Нет текста для озвучивания");
        if (clean.length() > 3500) clean = clean.substring(0, 3500);
        JSONObject request = new JSONObject();
        request.put("model", TTS_MODEL);
        request.put("input", clean);
        request.put("voice", TTS_VOICE);
        request.put("response_format", "pcm");

        HttpURLConnection connection = open("audio/speech", "application/json", "audio/pcm");
        activeConnection.set(connection);
        try {
            write(connection, request.toString().getBytes(StandardCharsets.UTF_8));
            int code = connection.getResponseCode();
            if (code < 200 || code >= 300) throw apiError(connection, code);
            byte[] pcm = readAll(new BufferedInputStream(connection.getInputStream()));
            if (pcm.length < 960) throw new IOException("RouterAI TTS вернул слишком короткое PCM-аудио");
            File output = new File(context.getCacheDir(), "tts_" + System.currentTimeMillis() + ".wav");
            writePcm16MonoWav(output, pcm, 24000);
            return output;
        } finally {
            activeConnection.compareAndSet(connection, null);
            connection.disconnect();
        }
    }

    private static void writePcm16MonoWav(File file, byte[] pcm, int sampleRate) throws IOException {
        int channels = 1;
        int bitsPerSample = 16;
        int byteRate = sampleRate * channels * bitsPerSample / 8;
        int blockAlign = channels * bitsPerSample / 8;
        ByteBuffer header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN);
        header.put("RIFF".getBytes(StandardCharsets.US_ASCII));
        header.putInt(36 + pcm.length);
        header.put("WAVE".getBytes(StandardCharsets.US_ASCII));
        header.put("fmt ".getBytes(StandardCharsets.US_ASCII));
        header.putInt(16);
        header.putShort((short) 1);
        header.putShort((short) channels);
        header.putInt(sampleRate);
        header.putInt(byteRate);
        header.putShort((short) blockAlign);
        header.putShort((short) bitsPerSample);
        header.put("data".getBytes(StandardCharsets.US_ASCII));
        header.putInt(pcm.length);
        try (FileOutputStream out = new FileOutputStream(file)) {
            out.write(header.array());
            out.write(pcm);
            out.flush();
        }
    }

'''
router = router[:method_start] + new_tts + router[method_end:]
client.write_text(router, encoding="utf-8")

checks = {
    "UiFactory setAllCaps": "button.setAllCaps(false);" in ui.read_text(encoding="utf-8"),
    "predictive back registration": "Api33BackDispatcher.register(this)" in text,
    "platform back dispatcher": "OnBackInvokedDispatcher.PRIORITY_DEFAULT" in text,
    "persistable URI read flag": "uri, Intent.FLAG_GRANT_READ_URI_PERMISSION" in text,
    "old text caps removed": "setTextAllCaps" not in ui.read_text(encoding="utf-8"),
    "old URI mask removed": "data.getFlags() &" not in text,
    "dynamic LLM humor": "локальные заготовки запрещены" in router and "chat/completions" in router,
    "Gemini TTS model": "google/gemini-3.1-flash-tts-preview" in router,
    "Zephyr voice": 'TTS_VOICE = "Zephyr"' in router,
    "PCM response": 'request.put("response_format", "pcm")' in router,
    "PCM WAV playback wrapper": "writePcm16MonoWav" in router and 'System.currentTimeMillis() + ".wav"' in router,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Source patch verification failed: " + ", ".join(failed))
print("Applied source fixes:", ", ".join(checks))
