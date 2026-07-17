package ru.demo.voice;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.graphics.SurfaceTexture;
import android.media.MediaPlayer;
import android.net.Uri;
import android.view.Surface;
import android.view.TextureView;

import java.io.IOException;

final class VideoLooper implements TextureView.SurfaceTextureListener {
    private final Context context;
    private final TextureView textureView;
    private MediaPlayer player;
    private Surface surface;
    private Uri pendingUri;
    private int pendingRawResource;
    private String pendingAssetPath;

    VideoLooper(Context context, TextureView textureView) {
        this.context = context.getApplicationContext();
        this.textureView = textureView;
        textureView.setSurfaceTextureListener(this);
    }

    void playAsset(String assetPath) {
        pendingAssetPath = assetPath;
        pendingUri = null;
        pendingRawResource = 0;
        if (textureView.isAvailable()) prepare();
    }

    void playRaw(int rawResourceId) {
        pendingAssetPath = null;
        pendingUri = null;
        pendingRawResource = rawResourceId;
        if (textureView.isAvailable()) prepare();
    }

    void playUri(Uri uri) {
        pendingAssetPath = null;
        pendingUri = uri;
        pendingRawResource = 0;
        if (textureView.isAvailable()) prepare();
    }

    void pause() {
        try { if (player != null && player.isPlaying()) player.pause(); } catch (Exception ignored) { }
    }

    void resume() {
        try { if (player != null && !player.isPlaying()) player.start(); } catch (Exception ignored) { }
    }

    void release() {
        releasePlayer();
        if (surface != null) {
            surface.release();
            surface = null;
        }
    }

    private void prepare() {
        releasePlayer();
        if (!textureView.isAvailable()) return;
        SurfaceTexture surfaceTexture = textureView.getSurfaceTexture();
        if (surfaceTexture == null) return;
        if (surface != null) surface.release();
        surface = new Surface(surfaceTexture);

        MediaPlayer newPlayer = new MediaPlayer();
        player = newPlayer;
        try {
            newPlayer.setSurface(surface);
            newPlayer.setLooping(true);
            newPlayer.setVolume(0f, 0f);
            if (pendingAssetPath != null) {
                try (AssetFileDescriptor afd = context.getAssets().openFd(pendingAssetPath)) {
                    newPlayer.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
                }
            } else if (pendingUri != null) {
                newPlayer.setDataSource(context, pendingUri);
            } else if (pendingRawResource != 0) {
                try (AssetFileDescriptor afd = context.getResources().openRawResourceFd(pendingRawResource)) {
                    if (afd == null) throw new IOException("Не удалось открыть видео");
                    newPlayer.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
                }
            } else {
                return;
            }
            newPlayer.setVideoScalingMode(MediaPlayer.VIDEO_SCALING_MODE_SCALE_TO_FIT);
            newPlayer.setOnPreparedListener(mp -> {
                textureView.setTransform(null);
                mp.start();
            });
            newPlayer.setOnErrorListener((mp, what, extra) -> true);
            newPlayer.prepareAsync();
        } catch (Exception e) {
            releasePlayer();
        }
    }

    private void releasePlayer() {
        if (player != null) {
            try { player.reset(); } catch (Exception ignored) { }
            try { player.release(); } catch (Exception ignored) { }
            player = null;
        }
    }

    @Override public void onSurfaceTextureAvailable(SurfaceTexture surfaceTexture, int width, int height) { prepare(); }
    @Override public void onSurfaceTextureSizeChanged(SurfaceTexture surfaceTexture, int width, int height) { textureView.setTransform(null); }
    @Override public boolean onSurfaceTextureDestroyed(SurfaceTexture surfaceTexture) {
        releasePlayer();
        if (surface != null) { surface.release(); surface = null; }
        return true;
    }
    @Override public void onSurfaceTextureUpdated(SurfaceTexture surfaceTexture) { }
}
