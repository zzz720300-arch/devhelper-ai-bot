from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / "pdf-engine-pdfbox/src/main/java/ru/pdfoffice/engine/pdfbox/PdfBoxOfficeSdk.kt"
text = source.read_text(encoding="utf-8")
replacements = {
    "            isOpen = false\n": "            setOpen(false)\n",
    "                        field.value = value\n": "                        field.setValue(value)\n",
    "                    canPrint = request.allowPrinting\n": "                    setCanPrint(request.allowPrinting)\n",
    "                    canExtractContent = request.allowCopying\n": "                    setCanExtractContent(request.allowCopying)\n",
    "                    canModify = request.allowModification\n": "                    setCanModify(request.allowModification)\n",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"Expected source fragment not found: {old!r}")
    text = text.replace(old, new, 1)
source.write_text(text, encoding="utf-8")
print(f"Patched {source}")
