import pdfplumber
from pathlib import Path
import re

pdf_dir = Path("data/pdfs")
time_re = re.compile(r"\d{1,2}:\d{2}")

for pdf_file in sorted(pdf_dir.glob("*.pdf")):
    with pdfplumber.open(str(pdf_file)) as pdf:
        count = 0
        total_count = 0 
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                # считаем строки, где есть время И порядковый номер в начале
                if re.match(r"^\s*\d+\s+", line) and time_re.search(line):
                    count += 1
                    total_count += count
        print(f"{pdf_file.name}: {count} data rows in PDF")

print(total_count)