# AI Image Finisher — Production Engine Gate V3

This branch contains only the verified engine-first source payload and CI required to execute four independent engines inside Android before any final product UI is accepted:

- Aire resize.
- BiRefNet/U2NetP background removal.
- Separate ncnn x2 and x4 super-resolution.
- VTracer Rust/JNI editable SVG vectorization.

The pull request must remain unmerged until Android instrumented tests pass and the Engine Gate artifact is produced.
