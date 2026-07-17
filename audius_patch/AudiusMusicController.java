package ru.demo.voice;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

final class AudiusMusicController {
    interface Listener {
        void onMusicSearching(String query);
        void onMusicStarted(String title, String artist);
        void onMusicPaused();
        void onMusicStopped();
        void onMusicError(String message);
    }

    private static final String API_BASE = "https://api.audius.co/v1";
    private static final String APP_NAME = "DemoVoice";

    private static final class Track {
        final String id;
        final String title;
        final String artist;
        final long plays;
        final int score;

        Track(String id, String title, String artist, long plays, int score) {
            this.id = id;
            this.title = title;
            this.artist = artist;
            this.plays = plays;
            this.score = score;
        }
    }

    private final Context context;
    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final AtomicInteger generation = new AtomicInteger();
    private final AudioManager audioManager;

    private MediaPlayer player;
    private AudioFocusRequest audioFocusRequest;
    private List<Track> queue = Collections.emptyList();
    private int queueIndex = -1;
    private boolean released;
    private boolean pausedForVoice;
    private boolean resumeAfterVoice;
    private float volume = 1.0f;

    AudiusMusicController(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
        this.audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
    }

    void playSearch(String rawQuery) {
        final String query = cleanQuery(rawQuery);
        if (query.isEmpty()) {
            listener.onMusicError("Не расслышала название песни");
            return;
        }
        cancelVoiceResume();
        final int token = generation.incrementAndGet();
        listener.onMusicSearching(query);
        network.execute(() -> {
            try {
                List<Track> found = search(query);
                if (released || token != generation.get()) return;
                main.post(() -> {
                    if (released || token != generation.get()) return;
                    if (found.isEmpty()) {
                        listener.onMusicError("В Audius ничего не нашлось");
                        return;
                    }
                    queue = found;
                    queueIndex = 0;
                    playQueueItem(token, 0);
                });
            } catch (Exception e) {
                if (released || token != generation.get()) return;
                main.post(() -> listener.onMusicError(readable(e)));
            }
        });
    }

    void next() {
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

    void pause() {
        cancelVoiceResume();
        try {
            if (player != null && player.isPlaying()) {
                player.pause();
                listener.onMusicPaused();
            }
        } catch (Exception ignored) { }
    }

    void resume() {
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

    void stop() {
        generation.incrementAndGet();
        cancelVoiceResume();
        queue = Collections.emptyList();
        queueIndex = -1;
        releasePlayer();
        abandonAudioFocus();
        listener.onMusicStopped();
    }

    void louder() {
        volume = Math.min(1f, volume + 0.15f);
        applyVolume();
    }

    void quieter() {
        volume = Math.max(0.08f, volume - 0.15f);
        applyVolume();
    }

    void pauseForVoice() {
        pausedForVoice = false;
        resumeAfterVoice = false;
        try {
            if (player != null && player.isPlaying()) {
                player.pause();
                pausedForVoice = true;
                resumeAfterVoice = true;
            }
        } catch (Exception ignored) { }
    }

    void cancelVoiceResume() {
        resumeAfterVoice = false;
        pausedForVoice = false;
    }

    void resumeAfterVoice() {
        if (!resumeAfterVoice || !pausedForVoice) return;
        resumeAfterVoice = false;
        pausedForVoice = false;
        try {
            if (player != null && !player.isPlaying()) {
                requestAudioFocus();
                player.start();
            }
        } catch (Exception ignored) { }
    }

    void release() {
        released = true;
        generation.incrementAndGet();
        releasePlayer();
        abandonAudioFocus();
        network.shutdownNow();
    }

    private void playQueueItem(int token, int index) {
        if (released || token != generation.get() || index < 0 || index >= queue.size()) return;
        releasePlayer();
        Track track = queue.get(index);
        MediaPlayer nextPlayer = new MediaPlayer();
        player = nextPlayer;
        try {
            nextPlayer.setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                    .build());
            String streamUrl = API_BASE + "/tracks/" + URLEncoder.encode(track.id, "UTF-8")
                    + "/stream?app_name=" + APP_NAME;
            Map<String, String> headers = new HashMap<>();
            headers.put("User-Agent", "DemoVoice/1.7 Android");
            headers.put("Accept", "audio/*,*/*");
            nextPlayer.setDataSource(context, Uri.parse(streamUrl), headers);
            nextPlayer.setVolume(volume, volume);
            nextPlayer.setOnPreparedListener(mp -> {
                if (released || token != generation.get() || mp != player) return;
                requestAudioFocus();
                mp.start();
                listener.onMusicStarted(track.title, track.artist);
            });
            nextPlayer.setOnCompletionListener(mp -> {
                if (released || token != generation.get()) return;
                int next = index + 1;
                if (next >= queue.size()) next = 0;
                queueIndex = next;
                playQueueItem(token, next);
            });
            nextPlayer.setOnErrorListener((mp, what, extra) -> {
                if (released || token != generation.get()) return true;
                int next = index + 1;
                if (next < queue.size()) {
                    queueIndex = next;
                    main.postDelayed(() -> playQueueItem(token, next), 200);
                } else {
                    listener.onMusicError("Найденные версии не удалось воспроизвести");
                }
                return true;
            });
            nextPlayer.prepareAsync();
        } catch (Exception e) {
            int next = index + 1;
            if (next < queue.size()) {
                queueIndex = next;
                playQueueItem(token, next);
            } else {
                listener.onMusicError("Не удалось открыть аудиопоток Audius");
            }
        }
    }

    private List<Track> search(String query) throws Exception {
        String url = API_BASE + "/tracks/search?query="
                + URLEncoder.encode(query, "UTF-8")
                + "&limit=20&sort_method=popular";
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(20_000);
        connection.setReadTimeout(30_000);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("User-Agent", "DemoVoice/1.7 Android");
        int code = connection.getResponseCode();
        InputStream stream = code >= 200 && code < 300
                ? connection.getInputStream() : connection.getErrorStream();
        byte[] body = readAll(stream);
        connection.disconnect();
        if (code < 200 || code >= 300) {
            throw new IOException("Audius ответил кодом " + code);
        }
        JSONObject root = new JSONObject(new String(body, StandardCharsets.UTF_8));
        JSONArray data = root.optJSONArray("data");
        if (data == null) return Collections.emptyList();

        ArrayList<Track> tracks = new ArrayList<>();
        String normalizedQuery = normalize(query);
        String[] tokens = significantTokens(normalizedQuery);
        for (int i = 0; i < data.length(); i++) {
            JSONObject item = data.optJSONObject(i);
            if (item == null) continue;
            String id = item.optString("id", "").trim();
            String title = item.optString("title", "").trim();
            if (id.isEmpty() || title.isEmpty()) continue;
            if (item.has("is_streamable") && !item.optBoolean("is_streamable", true)) continue;
            if (item.optBoolean("is_stream_gated", false)) continue;
            JSONObject access = item.optJSONObject("access");
            if (access != null && access.has("stream") && !access.optBoolean("stream", true)) continue;
            JSONObject user = item.optJSONObject("user");
            String artist = "";
            if (user != null) {
                artist = user.optString("name", "").trim();
                if (artist.isEmpty()) artist = user.optString("handle", "").trim();
            }
            long plays = item.optLong("play_count", 0L);
            String haystack = normalize(title + " " + artist);
            int score = similarityScore(normalizedQuery, tokens, haystack, normalize(title));
            tracks.add(new Track(id, title, artist, plays, score));
        }
        tracks.sort(new Comparator<Track>() {
            @Override public int compare(Track a, Track b) {
                int byScore = Integer.compare(b.score, a.score);
                if (byScore != 0) return byScore;
                return Long.compare(b.plays, a.plays);
            }
        });
        return tracks;
    }

    private static int similarityScore(String query, String[] tokens, String haystack, String title) {
        int score = 0;
        if (haystack.equals(query)) score += 1000;
        if (title.equals(query)) score += 900;
        if (haystack.contains(query)) score += 500;
        if (title.contains(query)) score += 450;
        for (String token : tokens) {
            if (title.contains(token)) score += 80;
            else if (haystack.contains(token)) score += 45;
        }
        return score;
    }

    private static String[] significantTokens(String text) {
        String[] raw = text.split("\\s+");
        ArrayList<String> result = new ArrayList<>();
        for (String token : raw) {
            if (token.length() >= 3) result.add(token);
        }
        return result.toArray(new String[0]);
    }

    private static String normalize(String value) {
        return value.toLowerCase(new Locale("ru", "RU"))
                .replace('ё', 'е')
                .replaceAll("[^a-zа-я0-9]+", " ")
                .trim()
                .replaceAll("\\s+", " ");
    }

    static String cleanQuery(String value) {
        if (value == null) return "";
        String q = value.trim();
        q = q.replaceFirst("(?iu)^\\s*(наташа|ника|демо)[,!.:?\\s]+", "");
        q = q.replaceFirst("(?iu)^\\s*(включи|поставь|запусти|сыграй|найди и включи|найди)\\s+", "");
        q = q.replaceFirst("(?iu)^\\s*(мне\\s+)?(песню|трек|композицию|музыку|песенку)\\s+", "");
        q = q.replaceAll("(?iu)\\s+(пожалуйста|если можно)\\s*$", "");
        return q.trim();
    }

    private Track currentTrack() {
        if (queueIndex < 0 || queueIndex >= queue.size()) return null;
        return queue.get(queueIndex);
    }

    private void applyVolume() {
        try { if (player != null) player.setVolume(volume, volume); } catch (Exception ignored) { }
    }

    private void requestAudioFocus() {
        if (audioManager == null) return;
        try {
            if (android.os.Build.VERSION.SDK_INT >= 26) {
                if (audioFocusRequest == null) {
                    audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                            .setAudioAttributes(new AudioAttributes.Builder()
                                    .setUsage(AudioAttributes.USAGE_MEDIA)
                                    .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                                    .build())
                            .setOnAudioFocusChangeListener(this::onAudioFocusChanged)
                            .build();
                }
                audioManager.requestAudioFocus(audioFocusRequest);
            }
        } catch (Exception ignored) { }
    }

    private void abandonAudioFocus() {
        if (audioManager == null || audioFocusRequest == null) return;
        try { audioManager.abandonAudioFocusRequest(audioFocusRequest); } catch (Exception ignored) { }
    }

    private void onAudioFocusChanged(int change) {
        try {
            if (player == null) return;
            if (change == AudioManager.AUDIOFOCUS_LOSS) {
                player.pause();
            } else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) {
                player.pause();
            } else if (change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) {
                player.setVolume(volume * 0.25f, volume * 0.25f);
            } else if (change == AudioManager.AUDIOFOCUS_GAIN) {
                player.setVolume(volume, volume);
            }
        } catch (Exception ignored) { }
    }

    private void releasePlayer() {
        MediaPlayer old = player;
        player = null;
        if (old != null) {
            try { old.setOnPreparedListener(null); } catch (Exception ignored) { }
            try { old.setOnCompletionListener(null); } catch (Exception ignored) { }
            try { old.setOnErrorListener(null); } catch (Exception ignored) { }
            try { old.reset(); } catch (Exception ignored) { }
            try { old.release(); } catch (Exception ignored) { }
        }
    }

    private static byte[] readAll(InputStream input) throws IOException {
        if (input == null) return new byte[0];
        try (BufferedInputStream in = new BufferedInputStream(input);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16 * 1024];
            int read;
            while ((read = in.read(buffer)) >= 0) out.write(buffer, 0, read);
            return out.toByteArray();
        }
    }

    private static String readable(Exception e) {
        String message = e.getMessage();
        if (message == null || message.trim().isEmpty()) return "Ошибка соединения с Audius";
        if (message.length() > 140) message = message.substring(0, 140);
        return message;
    }
}
