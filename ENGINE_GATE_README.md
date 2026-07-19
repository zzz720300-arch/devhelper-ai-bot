# AI Image Finisher Production Engine Gate

This temporary branch contains a SHA-256-verified source payload and a GitHub Actions workflow that builds and executes four independent Android image-processing engines before any product UI is accepted:

1. Aire resize.
2. BiRefNet/U2NetP background removal through ONNX Runtime Android.
3. Separate native ncnn x2 and x4 super-resolution models.
4. VTracer Rust/JNI editable SVG vectorization.

The workflow must produce Android instrumented-test evidence, AAR modules, native libraries and a technical self-test APK. The branch must not be merged until the Engine Gate passes.
