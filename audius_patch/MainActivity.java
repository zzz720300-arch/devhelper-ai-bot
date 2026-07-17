package ru.demo.voice;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.view.Gravity;
import android.view.HapticFeedbackConstants;
import android.view.TextureView;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.Toast;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

public final class MainActivity extends Activity
        implements RecognitionListener, AudiusMusicController.Listener {
    private static final int REQ_AUDIO = 1001;
    private static final String PREFS = "demo_settings";
    private static final String KEY_SLOT = "video_slot";
    private static final int VIDEO_COUNT = 9;

    private static final Pattern PLAY_MUSIC = Pattern.compile(
            "(?iu)^\\s*(?:(?:наташа|ника|демо)[,!.:?\\s]+)?(?:включи|поставь|запусти|сыграй|найди(?:\\s+и)?\\s+включи)\\b.+");

    private enum Phase { IDLE, LISTENING, THINKING, SPEAKING }

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final AtomicBoolean destroyed = new AtomicBoolean(false);

    private TextureView textureView;
    private VideoLooper videoLooper;
    private ImageButton previousButton;
    private ImageButton microphoneButton;
    private ImageButton nextButton;
    private SpeechRecognizer speechRecognizer;
    private Intent recognizerIntent;
    private TextToSpeech systemTts;
    private boolean systemTtsReady;
    private PcmPlayer pcmPlayer;
    private PromptManager promptManager;
    private ConversationStore conversationStore;
    private SharedPreferences settings;
    private AudiusMusicController musicController;
    private volatile Phase phase = Phase.IDLE;
    private volatile boolean requestInFlight;
    private volatile boolean musicBusy;
    private int currentSlot;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        enterImmersiveMode();

        settings = getSharedPreferences(PREFS, MODE_PRIVATE);
        currentSlot = clampSlot(settings.getInt(KEY_SLOT, 1));
        try {
            promptManager = new PromptManager(this);
        } catch (IOException e) {
            Toast.makeText(this, "Не удалось загрузить промпты", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        conversationStore = new ConversationStore(this);
        pcmPlayer = new PcmPlayer();
        musicController = new AudiusMusicController(this, this);

        buildInterface();
        initialiseSpeechRecognizer();
        initialiseSystemTts();
        loadCurrentVideo();
    }

    private void buildInterface() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        textureView = new TextureView(this);
        root.addView(textureView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        videoLooper = new VideoLooper(this, textureView);

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.HORIZONTAL);
        panel.setGravity(Gravity.CENTER);
        panel.setPadding(dp(8), dp(6), dp(8), dp(6));
        panel.setBackground(roundedBackground(0x8A77777C, dp(25), 0x28FFFFFF, 1));
        panel.setElevation(dp(8));

        previousButton = createPanelButton(R.drawable.ic_arrow_left, 52);
        microphoneButton = createPanelButton(R.drawable.ic_mic, 60);
        nextButton = createPanelButton(R.drawable.ic_arrow_right, 52);

        panel.addView(previousButton, buttonLayout(52, 0, 10));
        panel.addView(microphoneButton, buttonLayout(60, 10, 10));
        panel.addView(nextButton, buttonLayout(52, 10, 0));

        FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(
                dp(242), dp(72), Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        panelParams.bottomMargin = dp(18);
        root.addView(panel, panelParams);
        setContentView(root);

        previousButton.setOnClickListener(v -> switchVideo(-1));
        nextButton.setOnClickListener(v -> switchVideo(1));
        microphoneButton.setOnClickListener(v -> onMicrophonePressed());

        previousButton.setOnLongClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            conversationStore.clear();
            Toast.makeText(this, "История диалога очищена", Toast.LENGTH_SHORT).show();
            return true;
        });
        microphoneButton.setOnLongClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            conversationStore.clear();
            Toast.makeText(this, "История диалога очищена", Toast.LENGTH_SHORT).show();
            return true;
        });
        nextButton.setOnLongClickListener(v -> {
            v.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS);
            loadCurrentVideo();
            Toast.makeText(this, "Видео перезапущено", Toast.LENGTH_SHORT).show();
            return true;
        });
        updatePhase(Phase.IDLE);
    }

    private ImageButton createPanelButton(int icon, int sizeDp) {
        ImageButton button = new ImageButton(this);
        button.setImageResource(icon);
        button.setScaleType(ImageButton.ScaleType.CENTER);
        button.setPadding(dp(11), dp(11), dp(11), dp(11));
        button.setColorFilter(null);
        button.setBackground(roundedBackground(0x2FFFFFFF, dp(sizeDp / 2), 0x30FFFFFF, 1));
        button.setContentDescription(null);
        return button;
    }

    private LinearLayout.LayoutParams buttonLayout(int size, int left, int right) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(dp(size), dp(size));
        params.leftMargin = dp(left);
        params.rightMargin = dp(right);
        return params;
    }

    private void initialiseSpeechRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Toast.makeText(this, "На телефоне нет службы распознавания речи", Toast.LENGTH_LONG).show();
            return;
        }
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechRecognizer.setRecognitionListener(this);
        recognizerIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU");
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "ru-RU");
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
        recognizerIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
    }

    private void initialiseSystemTts() {
        systemTts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                systemTtsReady = true;
                int languageResult = systemTts.setLanguage(new Locale("ru", "RU"));
                if (languageResult == TextToSpeech.LANG_MISSING_DATA
                        || languageResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                    systemTts.setLanguage(Locale.getDefault());
                }
                systemTts.setSpeechRate(0.96f);
                systemTts.setPitch(1.02f);
                systemTts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                    @Override public void onStart(String utteranceId) {
                        mainHandler.post(() -> updatePhase(Phase.SPEAKING));
                    }
                    @Override public void onDone(String utteranceId) {
                        mainHandler.post(() -> finishAssistantSpeech());
                    }
                    @Override public void onError(String utteranceId) {
                        onDone(utteranceId);
                    }
                });
            }
        });
    }

    private void onMicrophonePressed() {
        if (phase == Phase.LISTENING) {
            if (speechRecognizer != null) speechRecognizer.stopListening();
            return;
        }
        if (musicBusy) {
            musicController.stop();
            musicBusy = false;
            updatePhase(Phase.IDLE);
            return;
        }
        if (phase == Phase.THINKING || phase == Phase.SPEAKING) {
            stopCurrentOperation();
            return;
        }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_AUDIO);
            return;
        }
        startListening();
    }

    private void startListening() {
        if (speechRecognizer == null || recognizerIntent == null) {
            Toast.makeText(this, "Распознавание речи недоступно", Toast.LENGTH_SHORT).show();
            return;
        }
        stopPlaybackOnly();
        musicController.pauseForVoice();
        try {
            updatePhase(Phase.LISTENING);
            speechRecognizer.startListening(recognizerIntent);
        } catch (Exception e) {
            updatePhase(Phase.IDLE);
            musicController.resumeAfterVoice();
            Toast.makeText(this, "Не удалось включить микрофон", Toast.LENGTH_SHORT).show();
        }
    }

    private boolean handleMusicCommand(String text) {
        String normalized = normalizeCommand(text);
        if (normalized.isEmpty()) return false;

        if (containsAny(normalized, "останови музыку", "выключи музыку", "стоп музыка",
                "хватит музыки", "останови песню", "выключи песню")) {
            musicController.cancelVoiceResume();
            musicController.stop();
            return true;
        }
        if (containsAny(normalized, "поставь на паузу", "пауза", "приостанови музыку",
                "приостанови песню")) {
            musicController.cancelVoiceResume();
            musicController.pause();
            return true;
        }
        if (containsAny(normalized, "продолжи музыку", "продолжи песню", "возобнови музыку",
                "сними с паузы")) {
            musicController.cancelVoiceResume();
            musicController.resume();
            return true;
        }
        if (containsAny(normalized, "следующая песня", "следующий трек", "другая песня",
                "включи следующую")) {
            musicController.cancelVoiceResume();
            musicController.next();
            return true;
        }
        if (containsAny(normalized, "музыку громче", "сделай громче", "громче музыку")) {
            musicController.cancelVoiceResume();
            musicController.louder();
            Toast.makeText(this, "Музыка громче", Toast.LENGTH_SHORT).show();
            return true;
        }
        if (containsAny(normalized, "музыку тише", "сделай тише", "тише музыку")) {
            musicController.cancelVoiceResume();
            musicController.quieter();
            Toast.makeText(this, "Музыка тише", Toast.LENGTH_SHORT).show();
            return true;
        }

        if (PLAY_MUSIC.matcher(text).matches()
                && !containsAny(normalized, "включи видео", "включи фон", "запусти видео")) {
            String query = AudiusMusicController.cleanQuery(text);
            if (!query.isEmpty()) {
                musicController.cancelVoiceResume();
                musicController.playSearch(query);
                return true;
            }
        }
        return false;
    }

    private void sendToAssistant(String userText) {
        if (TextUtil.isBlank(userText) || requestInFlight) return;
        requestInFlight = true;
        updatePhase(Phase.THINKING);
        worker.execute(() -> {
            try {
                PromptManager.PromptBundle prompt = promptManager.load();
                conversationStore.clearIfRoleChanged(prompt.roleHash);
                String key = promptManager.getApiKey();
                if (TextUtil.isBlank(key)) throw new IOException("Ключ RouterAI не задан");

                RouterAiClient client = new RouterAiClient(key);
                String answer = client.chat(
                        prompt.systemPrompt,
                        conversationStore.snapshot(),
                        userText.trim()
                );
                conversationStore.append("user", userText.trim());
                conversationStore.append("assistant", answer);

                try {
                    byte[] pcm = client.synthesizePcm(answer);
                    if (destroyed.get()) return;
                    mainHandler.post(() -> updatePhase(Phase.SPEAKING));
                    pcmPlayer.play(pcm, () -> mainHandler.post(this::finishAssistantSpeech));
                } catch (Exception ttsError) {
                    mainHandler.post(() -> speakWithSystemTts(answer));
                }
            } catch (Exception error) {
                mainHandler.post(() -> {
                    requestInFlight = false;
                    updatePhase(Phase.IDLE);
                    musicController.resumeAfterVoice();
                    Toast.makeText(this, readableError(error), Toast.LENGTH_LONG).show();
                });
            }
        });
    }

    private void finishAssistantSpeech() {
        requestInFlight = false;
        updatePhase(Phase.IDLE);
        musicController.resumeAfterVoice();
    }

    private void speakWithSystemTts(String answer) {
        if (destroyed.get()) return;
        if (systemTtsReady && systemTts != null) {
            updatePhase(Phase.SPEAKING);
            Bundle params = new Bundle();
            params.putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1f);
            int result = systemTts.speak(answer, TextToSpeech.QUEUE_FLUSH, params, "demo_answer");
            if (result == TextToSpeech.ERROR) {
                requestInFlight = false;
                updatePhase(Phase.IDLE);
                musicController.resumeAfterVoice();
                Toast.makeText(this, "Не удалось озвучить ответ", Toast.LENGTH_LONG).show();
            }
        } else {
            requestInFlight = false;
            updatePhase(Phase.IDLE);
            musicController.resumeAfterVoice();
            Toast.makeText(this, "Ответ получен, но TTS недоступен", Toast.LENGTH_LONG).show();
        }
    }

    private String readableError(Exception error) {
        if (error instanceof RouterAiClient.ApiException) {
            RouterAiClient.ApiException api = (RouterAiClient.ApiException) error;
            if (api.statusCode == 401 || api.statusCode == 403) return "RouterAI отклонил ключ";
            if (api.statusCode == 402) return "На балансе RouterAI недостаточно средств";
            if (api.statusCode == 429) return "Слишком много запросов. Повторите позже";
        }
        String message = error.getMessage();
        if (TextUtil.isBlank(message)) return "Ошибка соединения с RouterAI";
        if (message.length() > 180) message = message.substring(0, 180);
        return message;
    }

    private void switchVideo(int direction) {
        currentSlot = ((currentSlot - 1 + direction) % VIDEO_COUNT + VIDEO_COUNT) % VIDEO_COUNT + 1;
        settings.edit().putInt(KEY_SLOT, currentSlot).apply();
        loadCurrentVideo();
    }

    private void loadCurrentVideo() {
        videoLooper.playAsset(String.format(Locale.US, "videos/video_%02d.mp4", currentSlot));
    }

    private void stopCurrentOperation() {
        requestInFlight = false;
        if (speechRecognizer != null) {
            try { speechRecognizer.cancel(); } catch (Exception ignored) { }
        }
        stopPlaybackOnly();
        updatePhase(Phase.IDLE);
        musicController.resumeAfterVoice();
    }

    private void stopPlaybackOnly() {
        if (pcmPlayer != null) pcmPlayer.stop();
        if (systemTts != null) {
            try { systemTts.stop(); } catch (Exception ignored) { }
        }
    }

    private void updatePhase(Phase newPhase) {
        phase = newPhase;
        if (microphoneButton == null) return;
        switch (newPhase) {
            case LISTENING:
                microphoneButton.setImageResource(R.drawable.ic_stop);
                microphoneButton.setBackground(roundedBackground(
                        0xCCB1262E, dp(30), 0x80FFFFFF, 1));
                microphoneButton.animate().scaleX(1.08f).scaleY(1.08f).setDuration(160).start();
                break;
            case THINKING:
                microphoneButton.setImageResource(R.drawable.ic_mic);
                microphoneButton.setBackground(roundedBackground(
                        0xB26A6257, dp(30), 0x65FFFFFF, 1));
                microphoneButton.animate().rotationBy(180f).scaleX(1f).scaleY(1f)
                        .setDuration(360).start();
                break;
            case SPEAKING:
                microphoneButton.setImageResource(R.drawable.ic_stop);
                microphoneButton.setBackground(roundedBackground(
                        0xB2495968, dp(30), 0x70FFFFFF, 1));
                microphoneButton.animate().scaleX(1.05f).scaleY(1.05f).setDuration(160).start();
                break;
            case IDLE:
            default:
                microphoneButton.setImageResource(R.drawable.ic_mic);
                microphoneButton.setBackground(roundedBackground(
                        0x36FFFFFF, dp(30), 0x45FFFFFF, 1));
                microphoneButton.animate().rotation(0f).scaleX(1f).scaleY(1f)
                        .setDuration(160).start();
                break;
        }
    }

    private GradientDrawable roundedBackground(int fillColor, int radiusPx,
                                                int strokeColor, int strokeWidthDp) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fillColor);
        drawable.setCornerRadius(radiusPx);
        drawable.setStroke(dp(strokeWidthDp), strokeColor);
        return drawable;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int clampSlot(int slot) {
        return Math.max(1, Math.min(VIDEO_COUNT, slot));
    }

    private void enterImmersiveMode() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );
    }

    private static String normalizeCommand(String value) {
        return value == null ? "" : value.toLowerCase(new Locale("ru", "RU"))
                .replace('ё', 'е')
                .replaceAll("[^a-zа-я0-9]+", " ")
                .trim()
                .replaceAll("\\s+", " ");
    }

    private static boolean containsAny(String value, String... variants) {
        for (String variant : variants) {
            if (value.contains(variant)) return true;
        }
        return false;
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) enterImmersiveMode();
    }

    @Override
    protected void onResume() {
        super.onResume();
        enterImmersiveMode();
        if (videoLooper != null) videoLooper.resume();
    }

    @Override
    protected void onPause() {
        if (videoLooper != null) videoLooper.pause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        destroyed.set(true);
        stopCurrentOperation();
        if (musicController != null) musicController.release();
        if (speechRecognizer != null) speechRecognizer.destroy();
        if (systemTts != null) systemTts.shutdown();
        if (videoLooper != null) videoLooper.release();
        worker.shutdownNow();
        super.onDestroy();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_AUDIO) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startListening();
        } else {
            Toast.makeText(this, "Без доступа к микрофону разговор невозможен",
                    Toast.LENGTH_LONG).show();
        }
    }

    @Override public void onReadyForSpeech(Bundle params) { updatePhase(Phase.LISTENING); }
    @Override public void onBeginningOfSpeech() { }
    @Override public void onRmsChanged(float rmsdB) { }
    @Override public void onBufferReceived(byte[] buffer) { }
    @Override public void onEndOfSpeech() { updatePhase(Phase.THINKING); }

    @Override
    public void onError(int error) {
        requestInFlight = false;
        updatePhase(Phase.IDLE);
        musicController.resumeAfterVoice();
        if (error == SpeechRecognizer.ERROR_NO_MATCH
                || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                || error == SpeechRecognizer.ERROR_CLIENT) return;
        Toast.makeText(this, "Ошибка распознавания речи: " + error,
                Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) {
            updatePhase(Phase.IDLE);
            musicController.resumeAfterVoice();
            return;
        }
        String text = matches.get(0).trim();
        if (text.isEmpty()) {
            updatePhase(Phase.IDLE);
            musicController.resumeAfterVoice();
            return;
        }
        if (handleMusicCommand(text)) {
            requestInFlight = false;
            return;
        }
        sendToAssistant(text);
    }

    @Override public void onPartialResults(Bundle partialResults) { }
    @Override public void onEvent(int eventType, Bundle params) { }

    @Override
    public void onMusicSearching(String query) {
        musicBusy = true;
        updatePhase(Phase.THINKING);
        Toast.makeText(this, "Ищу в Audius: " + query, Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicStarted(String title, String artist) {
        musicBusy = false;
        updatePhase(Phase.IDLE);
        String text = TextUtil.isBlank(artist) ? title : title + " — " + artist;
        Toast.makeText(this, "Играет: " + text, Toast.LENGTH_LONG).show();
    }

    @Override
    public void onMusicPaused() {
        musicBusy = false;
        updatePhase(Phase.IDLE);
        Toast.makeText(this, "Музыка на паузе", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicStopped() {
        musicBusy = false;
        updatePhase(Phase.IDLE);
        Toast.makeText(this, "Музыка остановлена", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicError(String message) {
        musicBusy = false;
        updatePhase(Phase.IDLE);
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}
