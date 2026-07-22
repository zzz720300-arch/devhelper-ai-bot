from pathlib import Path

root = Path(__file__).resolve().parents[2]

build_file = root / "demo-app/build.gradle.kts"
build_text = build_file.read_text(encoding="utf-8")
needle = '    kotlinOptions { jvmTarget = "17" }\n'
replacement = '    kotlinOptions { jvmTarget = "17" }\n    buildFeatures { buildConfig = true }\n'
if replacement not in build_text:
    if needle not in build_text:
        raise SystemExit("demo-app kotlinOptions insertion point not found")
    build_text = build_text.replace(needle, replacement, 1)
build_file.write_text(build_text, encoding="utf-8")

activity = root / "demo-app/src/main/java/ru/pdfoffice/demo/MainActivity.kt"
activity_text = activity.read_text(encoding="utf-8")
needle = '            dirty = state.getBoolean("dirty", false),\n            lastSavedUri = state.getString("lastSavedUri")?.let(Uri::parse),\n'
replacement = '            dirty = state.getBoolean("dirty", false),\n            revision = state.getInt("revision", 0).coerceAtLeast(0),\n            lastSavedUri = state.getString("lastSavedUri")?.let(Uri::parse),\n'
if replacement not in activity_text:
    if needle not in activity_text:
        raise SystemExit("DocumentSession restore insertion point not found")
    activity_text = activity_text.replace(needle, replacement, 1)
activity.write_text(activity_text, encoding="utf-8")

print("Applied PDF Office Engine 1.1 BuildConfig and session revision hotfix")
