from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: apply_hotfix.py <project-root>")
root = Path(sys.argv[1]).resolve()

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

if "import android.annotation.SuppressLint\n" not in activity_text:
    activity_text = activity_text.replace("package ru.pdfoffice.demo\n\n", "package ru.pdfoffice.demo\n\nimport android.annotation.SuppressLint\n", 1)
if "import android.os.Build\n" not in activity_text:
    activity_text = activity_text.replace("import android.os.Bundle\n", "import android.os.Build\nimport android.os.Bundle\n", 1)
if "import android.window.OnBackInvokedDispatcher\n" not in activity_text:
    activity_text = activity_text.replace("import android.view.ViewGroup\n", "import android.view.ViewGroup\nimport android.window.OnBackInvokedDispatcher\n", 1)

needle = '        restoreState(savedInstanceState)\n        showHome()\n'
replacement = '        restoreState(savedInstanceState)\n        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {\n            onBackInvokedDispatcher.registerOnBackInvokedCallback(OnBackInvokedDispatcher.PRIORITY_DEFAULT) {\n                handleBackAction()\n            }\n        }\n        showHome()\n'
if replacement not in activity_text:
    if needle not in activity_text:
        raise SystemExit("onCreate predictive back insertion point not found")
    activity_text = activity_text.replace(needle, replacement, 1)

needle = '            outState.putBoolean("dirty", current.dirty)\n            outState.putString("lastSavedUri", current.lastSavedUri?.toString())\n'
replacement = '            outState.putBoolean("dirty", current.dirty)\n            outState.putInt("revision", current.revision)\n            outState.putString("lastSavedUri", current.lastSavedUri?.toString())\n'
if replacement not in activity_text:
    if needle not in activity_text:
        raise SystemExit("session revision save insertion point not found")
    activity_text = activity_text.replace(needle, replacement, 1)

needle = '            dirty = state.getBoolean("dirty", false),\n            lastSavedUri = state.getString("lastSavedUri")?.let(Uri::parse),\n'
replacement = '            dirty = state.getBoolean("dirty", false),\n            revision = state.getInt("revision", 0).coerceAtLeast(0),\n            lastSavedUri = state.getString("lastSavedUri")?.let(Uri::parse),\n'
if replacement not in activity_text:
    if needle not in activity_text:
        raise SystemExit("DocumentSession restore insertion point not found")
    activity_text = activity_text.replace(needle, replacement, 1)

needle = '''    @Deprecated("Retained for minSdk 26")
    override fun onBackPressed() {
        when (screen) {
            Screen.HOME -> super.onBackPressed()
            Screen.WORKSPACE -> handleWorkspaceBack()
            Screen.OPERATIONS -> showWorkspace()
            Screen.NEW_DOCUMENT -> showHome()
            Screen.DIAGNOSTICS -> if (session != null) showWorkspace() else showHome()
        }
    }
'''
replacement = '''    private fun handleBackAction() {
        when (screen) {
            Screen.HOME -> finish()
            Screen.WORKSPACE -> handleWorkspaceBack()
            Screen.OPERATIONS -> showWorkspace()
            Screen.NEW_DOCUMENT -> showHome()
            Screen.DIAGNOSTICS -> if (session != null) showWorkspace() else showHome()
        }
    }

    @SuppressLint("GestureBackNavigation")
    @Deprecated("Used as a fallback on Android 12 and earlier")
    override fun onBackPressed() {
        handleBackAction()
    }
'''
if replacement not in activity_text:
    if needle not in activity_text:
        raise SystemExit("legacy back handler block not found")
    activity_text = activity_text.replace(needle, replacement, 1)

activity.write_text(activity_text, encoding="utf-8")
print("Applied PDF Office Engine 1.1 BuildConfig, session and predictive-back hotfixes")
