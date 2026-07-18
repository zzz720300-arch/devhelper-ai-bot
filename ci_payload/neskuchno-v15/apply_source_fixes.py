#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])
ui = root / "app/src/main/java/ru/quantai/neskuchno/UiFactory.java"
main = root / "app/src/main/java/ru/quantai/neskuchno/MainActivity.java"

ui_text = ui.read_text(encoding="utf-8")
ui_text = ui_text.replace("button.setTextAllCaps(false);", "button.setAllCaps(false);")
ui.write_text(ui_text, encoding="utf-8")

text = main.read_text(encoding="utf-8")
if "import android.os.Build;" not in text:
    text = text.replace("import android.os.Bundle;\n", "import android.os.Build;\nimport android.os.Bundle;\n")

text = text.replace(
    "        storyRepository = new StoryRepository(this);\n        showHome();\n",
    "        storyRepository = new StoryRepository(this);\n        showHome();\n        if (Build.VERSION.SDK_INT >= 33) Api33BackDispatcher.register(this);\n",
)

text = text.replace(
    "            getContentResolver().takePersistableUriPermission(uri,\n"
    "                    data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION));",
    "            getContentResolver().takePersistableUriPermission(\n"
    "                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);",
)

old_back = '''    @Override public void onBackPressed() {\n        if (recorder.isRecording()) {\n            recorder.cancel();\n            Toast.makeText(this, "Запись отменена", Toast.LENGTH_SHORT).show();\n            return;\n        }\n        if (backAction != null) backAction.run();\n        else super.onBackPressed();\n    }\n'''
new_back = '''    @android.annotation.SuppressLint("GestureBackNavigation")\n    @SuppressWarnings("deprecation")\n    @Override public void onBackPressed() {\n        handleBackNavigation();\n    }\n\n    private void handleBackNavigation() {\n        if (recorder != null && recorder.isRecording()) {\n            recorder.cancel();\n            Toast.makeText(this, "Запись отменена", Toast.LENGTH_SHORT).show();\n            return;\n        }\n        if (backAction != null) backAction.run();\n        else finish();\n    }\n\n    @android.annotation.TargetApi(33)\n    private static final class Api33BackDispatcher {\n        static void register(MainActivity activity) {\n            activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(\n                    android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,\n                    activity::handleBackNavigation);\n        }\n    }\n'''
if old_back in text:
    text = text.replace(old_back, new_back)

main.write_text(text, encoding="utf-8")

checks = {
    "UiFactory setAllCaps": "button.setAllCaps(false);" in ui.read_text(encoding="utf-8"),
    "predictive back registration": "Api33BackDispatcher.register(this)" in text,
    "platform back dispatcher": "OnBackInvokedDispatcher.PRIORITY_DEFAULT" in text,
    "persistable URI read flag": "uri, Intent.FLAG_GRANT_READ_URI_PERMISSION" in text,
    "old text caps removed": "setTextAllCaps" not in ui.read_text(encoding="utf-8"),
    "old URI mask removed": "data.getFlags() &" not in text,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Source patch verification failed: " + ", ".join(failed))
print("Applied source fixes:", ", ".join(checks))
