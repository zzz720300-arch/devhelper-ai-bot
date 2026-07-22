from pathlib import Path

root = Path("ResearchDocMobile")

# Android API available on the CI image.
gradle = root / "app/build.gradle.kts"
text = gradle.read_text(encoding="utf-8")
text = text.replace("compileSdk = 37", "compileSdk = 36")
text = text.replace("targetSdk = 37", "targetSdk = 36")
gradle.write_text(text, encoding="utf-8")

# Secure XML parsing compatible with Android 8+.
validator = root / "app/src/main/java/ru/researchdoc/mobile/DocxValidator.java"
text = validator.read_text(encoding="utf-8")
text = text.replace("import javax.xml.XMLConstants;\n", "")
text = text.replace(
    "import java.io.File;\nimport java.io.InputStream;",
    "import java.io.ByteArrayOutputStream;\nimport java.io.File;\nimport java.io.InputStream;",
)
bad_xml = '        try{f.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD,"");f.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA,"");}catch(Exception ignored){}\n'
if bad_xml not in text:
    raise SystemExit("DocxValidator XML patch target not found")
text = text.replace(bad_xml, "")
old_read = '    private static String read(InputStream in)throws Exception{try(in){return new String(in.readAllBytes(),StandardCharsets.UTF_8);}}'
new_read = '''    private static String read(InputStream in)throws Exception{\n        try(in;ByteArrayOutputStream out=new ByteArrayOutputStream()){\n            byte[] buffer=new byte[8192];\n            int count;\n            while((count=in.read(buffer))!=-1)out.write(buffer,0,count);\n            return out.toString(StandardCharsets.UTF_8.name());\n        }\n    }'''
if old_read not in text:
    raise SystemExit("DocxValidator stream patch target not found")
validator.write_text(text.replace(old_read, new_read), encoding="utf-8")

# Avoid collision with ContentProvider.requireContext().
provider = root / "app/src/main/java/ru/researchdoc/mobile/ShareFileProvider.java"
text = provider.read_text(encoding="utf-8")
if "private Context requireContext()" not in text:
    raise SystemExit("ShareFileProvider patch target not found")
provider.write_text(text.replace("requireContext()", "providerContext()"), encoding="utf-8")

# Lambda captures must use variables that are effectively final.
engine = root / "app/src/main/java/ru/researchdoc/mobile/ResearchEngine.java"
text = engine.read_text(encoding="utf-8")
anchor = '        JSONObject plan=new JSONObject(JobStore.readJobText(context,job.id,"plan.json"));\n        List<SourceRecord> candidates=new ArrayList<>();'
replacement = '        JSONObject plan=new JSONObject(JobStore.readJobText(context,job.id,"plan.json"));\n        final JobRecord activeJob=job;\n        final JSONObject activePlan=plan;\n        List<SourceRecord> candidates=new ArrayList<>();'
if anchor not in text:
    raise SystemExit("ResearchEngine final-variable anchor not found")
text = text.replace(anchor, replacement)
replacements = {
    "writeSection(job,sections.get(index),index,total,accepted,draft.toString())": "writeSection(activeJob,sections.get(index),index,total,accepted,draft.toString())",
    'JobStore.file(context,job.id,"ResearchDoc_"+safeFileName(job.topic)+".docx")': 'JobStore.file(context,activeJob.id,"ResearchDoc_"+safeFileName(activeJob.topic)+".docx")',
    'DocxBuilder.build(out,plan.optString("title",job.topic),finalText,accepted)': 'DocxBuilder.build(out,activePlan.optString("title",activeJob.topic),finalText,accepted)',
    'plan.optString("title",job.topic),sections,accepted)': 'activePlan.optString("title",activeJob.topic),sections,accepted)',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"ResearchEngine patch target not found: {old}")
    text = text.replace(old, new)
engine.write_text(text, encoding="utf-8")

# Predictive back navigation and safe dynamic receiver registration.
activity = root / "app/src/main/java/ru/researchdoc/mobile/MainActivity.java"
text = activity.read_text(encoding="utf-8")
text = text.replace("import android.Manifest;\n", "import android.Manifest;\nimport android.annotation.SuppressLint;\n")
text = text.replace("import android.widget.Toast;\n", "import android.widget.Toast;\nimport android.window.OnBackInvokedDispatcher;\n")
old_create = "        buildUi();\n        requestNotificationPermission();"
new_create = '''        buildUi();\n        if (Build.VERSION.SDK_INT >= 33) {\n            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(\n                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::handleBackPressed);\n        }\n        requestNotificationPermission();'''
if old_create not in text:
    raise SystemExit("MainActivity onCreate patch target not found")
text = text.replace(old_create, new_create)
text = text.replace("    @Override protected void onStart() {", '    @SuppressLint("UnspecifiedRegisterReceiverFlag")\n    @Override protected void onStart() {')
old_back = '''    @Override public void onBackPressed() {\n        JobRecord job = JobStore.load(this, activeJobId);\n        if (job != null && job.isRunning()) {\n            new AlertDialog.Builder(this)\n                    .setTitle("Задача продолжит работу")\n                    .setMessage("Можно закрыть экран: исследование продолжится в фоне и сохранит результат.")\n                    .setNegativeButton("Остаться", null)\n                    .setPositiveButton("Закрыть экран", (d, w) -> MainActivity.super.onBackPressed())\n                    .show();\n        } else super.onBackPressed();\n    }\n'''
new_back = '''    @SuppressLint("GestureBackNavigation")\n    @Override public void onBackPressed() { handleBackPressed(); }\n\n    private void handleBackPressed() {\n        JobRecord job = JobStore.load(this, activeJobId);\n        if (job != null && job.isRunning()) {\n            new AlertDialog.Builder(this)\n                    .setTitle("Задача продолжит работу")\n                    .setMessage("Можно закрыть экран: исследование продолжится в фоне и сохранит результат.")\n                    .setNegativeButton("Остаться", null)\n                    .setPositiveButton("Закрыть экран", (d, w) -> finish())\n                    .show();\n        } else finish();\n    }\n'''
if old_back not in text:
    raise SystemExit("MainActivity back patch target not found")
activity.write_text(text.replace(old_back, new_back), encoding="utf-8")

print("ResearchDoc source fixes applied")
