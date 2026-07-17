from pathlib import Path

ROOT = Path("demo_rutube_src")
APP = ROOT / "app/src/main"
JAVA = APP / "java/ru/demo/voice"
DRAWABLE = APP / "res/drawable"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Patch target not found: {label}")
    return text.replace(old, new, 1)


main_path = JAVA / "MainActivity.java"
main = main_path.read_text(encoding="utf-8")

main = replace_once(
    main,
    "    private enum Phase { IDLE, LISTENING, THINKING, SPEAKING }\n",
    "    private enum Phase { IDLE, LISTENING, THINKING, SPEAKING }\n"
    "    private enum ListeningTarget { ASSISTANT, MUSIC_SEARCH }\n",
    "listening target enum",
)

main = replace_once(
    main,
    "    private ImageButton previousButton;\n"
    "    private ImageButton microphoneButton;\n"
    "    private ImageButton nextButton;\n",
    "    private ImageButton previousButton;\n"
    "    private ImageButton microphoneButton;\n"
    "    private ImageButton nextButton;\n"
    "    private ImageButton playerModeButton;\n"
    "    private LinearLayout musicControlPanel;\n"
    "    private ImageButton musicPreviousButton;\n"
    "    private ImageButton musicPlayPauseButton;\n"
    "    private ImageButton musicNextButton;\n"
    "    private ImageButton musicSearchButton;\n",
    "player UI fields",
)

main = replace_once(
    main,
    "    private volatile boolean requestInFlight;\n"
    "    private volatile boolean musicBusy;\n"
    "    private int currentSlot;\n",
    "    private volatile boolean requestInFlight;\n"
    "    private volatile boolean musicBusy;\n"
    "    private volatile boolean musicPlaying;\n"
    "    private boolean playerMode;\n"
    "    private ListeningTarget listeningTarget = ListeningTarget.ASSISTANT;\n"
    "    private int currentSlot;\n",
    "player state fields",
)

old_ui = """        previousButton = createPanelButton(R.drawable.ic_arrow_left, 52);
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
"""

new_ui = """        previousButton = createPanelButton(R.drawable.ic_arrow_left, 52);
        microphoneButton = createPanelButton(R.drawable.ic_mic, 60);
        nextButton = createPanelButton(R.drawable.ic_arrow_right, 52);
        playerModeButton = createPanelButton(R.drawable.ic_player_mode, 52);

        panel.addView(previousButton, buttonLayout(52, 0, 8));
        panel.addView(microphoneButton, buttonLayout(60, 8, 8));
        panel.addView(nextButton, buttonLayout(52, 8, 8));
        panel.addView(playerModeButton, buttonLayout(52, 8, 0));

        FrameLayout.LayoutParams panelParams = new FrameLayout.LayoutParams(
                dp(296), dp(72), Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        panelParams.bottomMargin = dp(18);
        root.addView(panel, panelParams);

        musicControlPanel = new LinearLayout(this);
        musicControlPanel.setOrientation(LinearLayout.HORIZONTAL);
        musicControlPanel.setGravity(Gravity.CENTER);
        musicControlPanel.setPadding(dp(8), dp(6), dp(8), dp(6));
        musicControlPanel.setBackground(roundedBackground(0x8A77777C, dp(24), 0x32FFFFFF, 1));
        musicControlPanel.setElevation(dp(8));
        musicControlPanel.setVisibility(View.GONE);

        musicPreviousButton = createPanelButton(R.drawable.ic_media_previous_custom, 50);
        musicPlayPauseButton = createPanelButton(R.drawable.ic_media_play_custom, 50);
        musicNextButton = createPanelButton(R.drawable.ic_media_next_custom, 50);
        musicSearchButton = createPanelButton(R.drawable.ic_music_search, 50);

        musicControlPanel.addView(musicPreviousButton, buttonLayout(50, 0, 8));
        musicControlPanel.addView(musicPlayPauseButton, buttonLayout(50, 8, 8));
        musicControlPanel.addView(musicNextButton, buttonLayout(50, 8, 8));
        musicControlPanel.addView(musicSearchButton, buttonLayout(50, 8, 0));

        FrameLayout.LayoutParams musicPanelParams = new FrameLayout.LayoutParams(
                dp(276), dp(68), Gravity.TOP | Gravity.CENTER_HORIZONTAL);
        musicPanelParams.topMargin = dp(18);
        root.addView(musicControlPanel, musicPanelParams);
        setContentView(root);

        previousButton.setOnClickListener(v -> switchVideo(-1));
        nextButton.setOnClickListener(v -> switchVideo(1));
        microphoneButton.setOnClickListener(v -> onMicrophonePressed());
        playerModeButton.setOnClickListener(v -> onPlayerModePressed());
        musicPreviousButton.setOnClickListener(v -> musicController.previous());
        musicPlayPauseButton.setOnClickListener(v -> toggleMusicPlayback());
        musicNextButton.setOnClickListener(v -> musicController.next());
        musicSearchButton.setOnClickListener(v -> startMusicSearchListening());
"""
main = replace_once(main, old_ui, new_ui, "buildInterface controls")

main = replace_once(
    main,
    "        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)\n"
    "                != PackageManager.PERMISSION_GRANTED) {\n",
    "        listeningTarget = ListeningTarget.ASSISTANT;\n"
    "        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)\n"
    "                != PackageManager.PERMISSION_GRANTED) {\n",
    "assistant listening target",
)

insert_before_listen = """    private void onPlayerModePressed() {
        if (!playerMode) {
            enterPlayerMode();
            return;
        }
        moveTaskToBack(true);
    }

    private void enterPlayerMode() {
        playerMode = true;
        if (musicControlPanel != null) musicControlPanel.setVisibility(View.VISIBLE);
        if (playerModeButton != null) {
            playerModeButton.setImageResource(R.drawable.ic_square_minimize);
            playerModeButton.setBackground(roundedBackground(
                    0x62525862, dp(26), 0x50FFFFFF, 1));
        }
        Toast.makeText(this,
                "Плеер включён. Для новой песни нажмите поиск сверху",
                Toast.LENGTH_SHORT).show();
    }

    private void startMusicSearchListening() {
        if (!playerMode) enterPlayerMode();
        if (phase == Phase.LISTENING) {
            if (speechRecognizer != null) speechRecognizer.stopListening();
            return;
        }
        if (phase == Phase.THINKING || phase == Phase.SPEAKING) {
            stopCurrentOperation();
        }
        listeningTarget = ListeningTarget.MUSIC_SEARCH;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_AUDIO);
            return;
        }
        startListening();
    }

    private void toggleMusicPlayback() {
        if (musicPlaying) musicController.pause();
        else musicController.resume();
    }

    private void updateMusicPlaybackState(boolean playing) {
        musicPlaying = playing;
        if (musicPlayPauseButton != null) {
            musicPlayPauseButton.setImageResource(playing
                    ? R.drawable.ic_media_pause_custom
                    : R.drawable.ic_media_play_custom);
        }
    }

"""
main = replace_once(
    main,
    "    private void startListening() {\n",
    insert_before_listen + "    private void startListening() {\n",
    "player methods",
)

old_results = """        if (handleMusicCommand(text)) {
            requestInFlight = false;
            return;
        }
        sendToAssistant(text);
"""
new_results = """        ListeningTarget target = listeningTarget;
        listeningTarget = ListeningTarget.ASSISTANT;
        if (target == ListeningTarget.MUSIC_SEARCH) {
            requestInFlight = false;
            updatePhase(Phase.IDLE);
            String query = AudiusMusicController.cleanQuery(text);
            if (query.isEmpty()) {
                musicController.resumeAfterVoice();
                Toast.makeText(this, "Не расслышала название композиции",
                        Toast.LENGTH_SHORT).show();
            } else {
                musicController.playSearch(query);
            }
            return;
        }
        sendToAssistant(text);
"""
main = replace_once(main, old_results, new_results, "route player search results")

old_error = """    @Override
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
"""
new_error = """    @Override
    public void onError(int error) {
        ListeningTarget failedTarget = listeningTarget;
        listeningTarget = ListeningTarget.ASSISTANT;
        requestInFlight = false;
        updatePhase(Phase.IDLE);
        musicController.resumeAfterVoice();
        if (error == SpeechRecognizer.ERROR_NO_MATCH
                || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                || error == SpeechRecognizer.ERROR_CLIENT) {
            if (failedTarget == ListeningTarget.MUSIC_SEARCH) {
                Toast.makeText(this, "Не расслышала название композиции",
                        Toast.LENGTH_SHORT).show();
            }
            return;
        }
        Toast.makeText(this, "Ошибка распознавания речи: " + error,
                Toast.LENGTH_SHORT).show();
    }
"""
main = replace_once(main, old_error, new_error, "speech error routing")

main = main.replace(
    'Toast.makeText(this, "Без доступа к микрофону разговор невозможен",\n'
    '                    Toast.LENGTH_LONG).show();',
    'Toast.makeText(this, "Без доступа к микрофону голосовой поиск и разговор недоступны",\n'
    '                    Toast.LENGTH_LONG).show();',
)

old_callbacks = """    @Override
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
"""
new_callbacks = """    @Override
    public void onMusicSearching(String query) {
        if (!playerMode) enterPlayerMode();
        musicBusy = true;
        updatePhase(Phase.THINKING);
        Toast.makeText(this, "Ищу в Audius: " + query, Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicStarted(String title, String artist) {
        musicBusy = false;
        updateMusicPlaybackState(true);
        updatePhase(Phase.IDLE);
        String text = TextUtil.isBlank(artist) ? title : title + " — " + artist;
        Toast.makeText(this, "Играет: " + text, Toast.LENGTH_LONG).show();
    }

    @Override
    public void onMusicPaused() {
        musicBusy = false;
        updateMusicPlaybackState(false);
        updatePhase(Phase.IDLE);
        Toast.makeText(this, "Музыка на паузе", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicStopped() {
        musicBusy = false;
        updateMusicPlaybackState(false);
        updatePhase(Phase.IDLE);
        Toast.makeText(this, "Музыка остановлена", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onMusicError(String message) {
        musicBusy = false;
        updateMusicPlaybackState(false);
        updatePhase(Phase.IDLE);
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
"""
main = replace_once(main, old_callbacks, new_callbacks, "music callbacks")
main_path.write_text(main, encoding="utf-8")


controller_path = JAVA / "AudiusMusicController.java"
controller = controller_path.read_text(encoding="utf-8")

controller = replace_once(
    controller,
    "        cancelVoiceResume();\n"
    "        final int token = generation.incrementAndGet();\n",
    "        final boolean resumePreviousOnFailure = resumeAfterVoice && pausedForVoice;\n"
    "        cancelVoiceResume();\n"
    "        final int token = generation.incrementAndGet();\n",
    "remember playback before search",
)
controller = replace_once(
    controller,
    "                    if (found.isEmpty()) {\n"
    "                        listener.onMusicError(\"В Audius ничего не нашлось\");\n"
    "                        return;\n"
    "                    }\n",
    "                    if (found.isEmpty()) {\n"
    "                        listener.onMusicError(\"В Audius ничего не нашлось\");\n"
    "                        if (resumePreviousOnFailure) resume();\n"
    "                        return;\n"
    "                    }\n",
    "resume after empty search",
)
controller = replace_once(
    controller,
    "                main.post(() -> listener.onMusicError(readable(e)));\n",
    "                main.post(() -> {\n"
    "                    listener.onMusicError(readable(e));\n"
    "                    if (resumePreviousOnFailure) resume();\n"
    "                });\n",
    "resume after search error",
)

next_method = """    void next() {
        cancelVoiceResume();
        if (queue.isEmpty()) {
            listener.onMusicError("Сначала включите песню");
            return;
        }
        int next = queueIndex + 1;
        if (next >= queue.size()) next = 0;
        int token = generation.incrementAndGet();
        queueIndex = next;
        playQueueItem(token, next);
    }

"""
previous_and_next = """    void previous() {
        cancelVoiceResume();
        if (queue.isEmpty()) {
            listener.onMusicError("Сначала найдите песню");
            return;
        }
        int previous = queueIndex - 1;
        if (previous < 0) previous = queue.size() - 1;
        int token = generation.incrementAndGet();
        queueIndex = previous;
        playQueueItem(token, previous);
    }

""" + next_method
controller = replace_once(controller, next_method, previous_and_next, "previous track method")

old_resume = """    void resume() {
        cancelVoiceResume();
        try {
            if (player != null && !player.isPlaying()) {
                requestAudioFocus();
                player.start();
                Track track = currentTrack();
                if (track != null) listener.onMusicStarted(track.title, track.artist);
            }
        } catch (Exception e) {
            listener.onMusicError("Не удалось продолжить музыку");
        }
    }
"""
new_resume = """    void resume() {
        cancelVoiceResume();
        if (player == null) {
            listener.onMusicError("Сначала найдите песню");
            return;
        }
        try {
            if (!player.isPlaying()) {
                requestAudioFocus();
                player.start();
                Track track = currentTrack();
                if (track != null) listener.onMusicStarted(track.title, track.artist);
            }
        } catch (Exception e) {
            listener.onMusicError("Не удалось продолжить музыку");
        }
    }
"""
controller = replace_once(controller, old_resume, new_resume, "resume without track")
controller = controller.replace("DemoVoice/1.7 Android", "DemoVoice/1.8 Android")
controller_path.write_text(controller, encoding="utf-8")


gradle_path = ROOT / "app/build.gradle"
gradle = gradle_path.read_text(encoding="utf-8")
gradle = gradle.replace("versionCode 10", "versionCode 11")
gradle = gradle.replace("versionName '1.7.0'", "versionName '1.8.0'")
gradle_path.write_text(gradle, encoding="utf-8")

DRAWABLE.mkdir(parents=True, exist_ok=True)
icons = {
    "ic_player_mode.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"32dp\" android:height=\"32dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M8,5v14l11,-7z\"/></vector>""",
    "ic_square_minimize.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M7,7h10v10H7z\"/></vector>""",
    "ic_media_previous_custom.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M6,6h2v12H6zM18,6v12l-9,-6z\"/></vector>""",
    "ic_media_next_custom.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M16,6h2v12h-2zM6,6l9,6l-9,6z\"/></vector>""",
    "ic_media_play_custom.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M8,5v14l11,-7z\"/></vector>""",
    "ic_media_pause_custom.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M7,5h4v14H7zM13,5h4v14h-4z\"/></vector>""",
    "ic_music_search.xml": """<vector xmlns:android=\"http://schemas.android.com/apk/res/android\" android:width=\"30dp\" android:height=\"30dp\" android:viewportWidth=\"24\" android:viewportHeight=\"24\"><path android:fillColor=\"#FFFFFFFF\" android:pathData=\"M9.5,4a5.5,5.5 0,1 0,0 11a5.5,5.5 0,0 0,0 -11M9.5,6a3.5,3.5 0,1 1,0 7a3.5,3.5 0,0 1,0 -7M14,13l6,6l-1.5,1.5l-6,-6z\"/></vector>""",
}
for name, content in icons.items():
    (DRAWABLE / name).write_text(content + "\n", encoding="utf-8")

print("Player UI patch applied successfully")
