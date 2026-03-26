from __future__ import annotations

import json
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def norm(v):
    if v is None:
        return ""
    s = str(v).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(2) if digits else s


def main():
    lines = load_json("data/lines.json")
    variant_stats = load_json("output/analytics/variant_stats.json")
    headways = load_json("output/analytics/headways.json")

    stats_by_line = {}
    for row in variant_stats:
        key = norm(row.get("line_no"))
        if key:
            stats_by_line.setdefault(key, []).append(row)

    headways_by_line = {}
    for row in headways:
        key = norm(row.get("line_no"))
        if key:
            headways_by_line.setdefault(key, []).append(row)

    matched = 0

    for line in lines:
        key = norm(line.get("code"))
        line["timetable_stats"] = stats_by_line.get(key, [])
        line["timetable_headways"] = headways_by_line.get(key, [])

        if line["timetable_stats"] or line["timetable_headways"]:
            matched += 1

    save_json(lines, "output/lines_with_timetables.json")

    print("Saved: output/lines_with_timetables.json")
    print("Matched lines with timetable data:", matched)

    for line in lines:
        key = norm(line.get("code"))
        stats_count = len(line.get("timetable_stats", []))
        headways_count = len(line.get("timetable_headways", []))
        if stats_count or headways_count:
            print(f"line {key}: stats={stats_count}, headways={headways_count}")


if __name__ == "__main__":
    main()