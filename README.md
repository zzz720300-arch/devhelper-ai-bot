# TextIllustrator 1.0.4 personal build branch

This branch stores a compressed source payload and a reproducible GitHub Actions build workflow for the personal Android application TextIllustrator.

The build restores source, runs unit tests and Android Lint, builds the R8-enabled release APK, creates a source ZIP and publishes reports and SHA-256 hashes as a workflow artifact.

No API key is committed. The application supports secure personal key entry using Android Keystore.
