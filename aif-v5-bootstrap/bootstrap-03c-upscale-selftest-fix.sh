#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?target project directory required}"
FILE="$ROOT/engine/upscale-ncnn/src/main/java/ru/quantai/imagefinisher/engine/upscale/NcnnUpscaleEngine.kt"
python3 - "$FILE" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
old = 'override suspend fun selfTest():EngineHealth=runCatching{check(File(context.applicationInfo.nativeLibraryDir,"libimagefinisher_upscale.so").isFile);val test='
new = 'override suspend fun selfTest():EngineHealth=runCatching{val test='
if old not in s:
    raise SystemExit('Expected brittle native-library file check was not found')
p.write_text(s.replace(old, new))
PY
! grep -q 'nativeLibraryDir' "$FILE"
grep -q 'val x2=upscale' "$FILE"
grep -q 'val x4=upscale' "$FILE"
