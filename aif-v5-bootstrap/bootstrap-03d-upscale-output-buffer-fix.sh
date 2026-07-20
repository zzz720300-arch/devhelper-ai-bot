#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
FILE="$ROOT/engine/upscale-ncnn/src/main/cpp/realsr_jni.cpp"
python3 - "$FILE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'ncnn::Mat in(w,h,bytes.data(),(size_t)4u,4); ncnn::Mat out; int rc=e->sr->process(in,out); if(rc!=0 || out.empty()) return nullptr;'
new = 'ncnn::Mat in(w,h,bytes.data(),(size_t)4u,4); ncnn::Mat out(w*e->scale,h*e->scale,(size_t)4u,4); if(out.empty()){ LOGE("output allocation failed %dx%d x%d",w,h,e->scale); return nullptr; } int rc=e->sr->process(in,out); if(rc!=0 || out.empty()){ LOGE("RealSR process failed rc=%d",rc); return nullptr; }'
if old not in s:
    raise SystemExit('Expected empty RealSR output Mat pattern was not found')
p.write_text(s.replace(old, new))
PY
grep -q 'ncnn::Mat out(w\*e->scale,h\*e->scale,(size_t)4u,4)' "$FILE"
! grep -q 'ncnn::Mat out; int rc=e->sr->process' "$FILE"
