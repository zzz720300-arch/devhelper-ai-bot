#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
FILE="$ROOT/engine/background-onnx/src/main/java/ru/quantai/imagefinisher/engine/background/BiRefNetBackgroundEngine.kt"
python3 - "$FILE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
s = s.replace(
    'import android.graphics.Paint\n',
    'import android.graphics.Paint\nimport android.os.Debug\nimport android.util.Log\n'
)
s = s.replace(
    'override suspend fun removeBackground(input: Bitmap, request: BackgroundRequest, progress: ProgressListener): Bitmap = withContext(Dispatchers.Default) {\n        val spec =',
    'override suspend fun removeBackground(input: Bitmap, request: BackgroundRequest, progress: ProgressListener): Bitmap = withContext(Dispatchers.Default) {\n        Log.e("AIF_BG", "START quality=${request.quality} input=${input.width}x${input.height} nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        val spec ='
)
s = s.replace(
    'val prepared = letterbox(source, spec.size)\n        progress.onProgress(1,3)\n        val mask = inferMask(session(request.quality, spec), prepared.bitmap, spec)\n        progress.onProgress(2,3)',
    'val prepared = letterbox(source, spec.size)\n        Log.e("AIF_BG", "PREPARED modelSize=${spec.size} content=${prepared.contentWidth}x${prepared.contentHeight} nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        progress.onProgress(1,3)\n        Log.e("AIF_BG", "INFERENCE_BEGIN nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        val mask = inferMask(session(request.quality, spec), prepared.bitmap, spec)\n        Log.e("AIF_BG", "INFERENCE_END mask=${mask.width}x${mask.height} nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        progress.onProgress(2,3)'
)
s = s.replace(
    'val scaled = Aire.scale(cropped, source.width, source.height, ResizeFunction.Bilinear, ScaleColorSpace.SRGB)\n        progress.onProgress(3,3)\n        applyMask(source, scaled)',
    'val scaled = Aire.scale(cropped, source.width, source.height, ResizeFunction.Bilinear, ScaleColorSpace.SRGB)\n        Log.e("AIF_BG", "MASK_SCALED output=${scaled.width}x${scaled.height} nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        progress.onProgress(3,3)\n        applyMask(source, scaled).also { Log.e("AIF_BG", "COMPLETE nativeHeap=${Debug.getNativeHeapAllocatedSize()}") }'
)
s = s.replace(
    'val file = ModelFileInstaller.install(context, spec.fileName, spec.sha256)\n        val options =',
    'val file = ModelFileInstaller.install(context, spec.fileName, spec.sha256)\n        Log.e("AIF_BG", "MODEL_READY file=${file.name} bytes=${file.length()} nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        val options ='
)
s = s.replace(
    'return env.createSession(file.absolutePath, options).also {',
    'Log.e("AIF_BG", "SESSION_CREATE_BEGIN nativeHeap=${Debug.getNativeHeapAllocatedSize()}")\n        return env.createSession(file.absolutePath, options).also { Log.e("AIF_BG", "SESSION_CREATE_END nativeHeap=${Debug.getNativeHeapAllocatedSize()}");'
)
required = ['AIF_BG', 'INFERENCE_BEGIN', 'SESSION_CREATE_BEGIN', 'MASK_SCALED']
for needle in required:
    if needle not in s:
        raise SystemExit(f'missing runtime marker: {needle}')
p.write_text(s)
PY
grep -q 'INFERENCE_BEGIN' "$FILE"
grep -q 'SESSION_CREATE_END' "$FILE"
grep -q 'Debug.getNativeHeapAllocatedSize' "$FILE"
