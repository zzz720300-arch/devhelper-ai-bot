#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
FILE="$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp"
python3 - "$FILE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = '''    ncnn::Mat in(width, height, bytes.data(), static_cast<size_t>(4u), 4);
    ncnn::Mat out;
    const int rc = engine->sr->process(in, out);
    if (rc != 0 || out.empty()) return nullptr;
'''
new = '''    ncnn::Mat in(width, height, bytes.data(), static_cast<size_t>(4u), 4);
    ncnn::Mat out(
        width * engine->scale,
        height * engine->scale,
        static_cast<size_t>(4u),
        4
    );
    if (out.empty()) {
        LOGE("Output allocation failed: %dx%d scale=%d", width, height, engine->scale);
        return nullptr;
    }
    const int rc = engine->sr->process(in, out);
    if (rc != 0 || out.empty()) {
        LOGE("RealSR process failed: rc=%d", rc);
        return nullptr;
    }
'''
if old not in s:
    raise SystemExit('Expected formatted empty RealSR output Mat pattern was not found')
p.write_text(s.replace(old, new))
PY
grep -q 'width \* engine->scale' "$FILE"
grep -q 'Output allocation failed' "$FILE"
! grep -q '^    ncnn::Mat out;$' "$FILE"
