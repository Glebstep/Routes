from __future__ import annotations

from pathlib import Path

from pdf_timetable_parser import parse_pdf_timetable, save_csv, save_json


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Parse all timetable PDFs")
    parser.add_argument("--pdf-dir", default="data/pdfs")
    parser.add_argument("--out-dir", default="output/timetables")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        raise SystemExit(f"No PDF files found in {pdf_dir}")

    all_records = []

    for pdf_file in pdf_files:
        print(f"Parsing {pdf_file.name}...")
        try:
            records = parse_pdf_timetable(pdf_file)
            if not records:
                print("  no rows parsed")
                continue

            save_json(records, out_dir / f"{pdf_file.stem}_trips.json")
            save_csv(records, out_dir / f"{pdf_file.stem}_trips.csv")
            all_records.extend(records)

            print(f"  parsed {len(records)} rows")
        except Exception as e:
            print(f"  failed: {e}")

    if all_records:
        save_json(all_records, out_dir / "all_trips.json")
        save_csv(all_records, out_dir / "all_trips.csv")
        print(f"\nDone. Total parsed rows: {len(all_records)}")
        print(f"Saved to: {out_dir}")


if __name__ == "__main__":
    main()