"""
Heraklion Bus Data — full pipeline.
 
Usage:
    python run_all.py          # run everything
    python run_all.py --skip-pdf   # skip PDF parsing (use cached timetables)
"""
import subprocess
import sys
import os
 
STEPS = [
    ("1. Process raw data (lines, stops, points)",
     [sys.executable, "process.py"]),
 
    ("2. Parse PDF timetables",
     [sys.executable, "parse_all_pdfs.py"]),
 
    ("3. Build timetable analytics (stats + headways)",
     [sys.executable, "build_timetable_stats.py"]),
 
    ("4. Link timetables to lines",
     [sys.executable, "link_timetables_to_routes.py"]),
 
    ("5. Merge timetables into GeoJSON",
     [sys.executable, "merge_timetable_into_routes.py"]),
 
    ("6. Generate interactive map",
     [sys.executable, "generate_map.py"]),
]
 
 
def main():
    skip_pdf = "--skip-pdf" in sys.argv
 
    for title, cmd in STEPS:
        if skip_pdf and "parse_all_pdfs" in cmd[1]:
            print(f"\n{'='*60}\nSKIPPED: {title}\n{'='*60}")
            continue
 
        print(f"\n{'='*60}\n{title}\n{'='*60}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\nFAILED at step: {title}")
            sys.exit(1)
 
    print(f"\n{'='*60}")
    print("DONE! Open output/map.html in browser.")
    print(f"{'='*60}")
 
 
if __name__ == "__main__":
    main()