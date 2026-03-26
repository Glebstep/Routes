from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


def load_csv(path: str | Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(rows: list[dict], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_json(obj, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build_variant_stats(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)

    for row in rows:
        key = (
            row.get("line_no"),
            row.get("service_type"),
            row.get("variant"),
            row.get("note"),
        )
        grouped[key].append(int(row["trip_minutes"]))

    result = []
    for (line_no, service_type, variant, note), values in grouped.items():
        result.append({
            "line_no": line_no,
            "service_type": service_type,
            "variant": variant,
            "note": note,
            "trip_count": len(values),
            "min_trip_minutes": min(values),
            "max_trip_minutes": max(values),
            "avg_trip_minutes": round(sum(values) / len(values), 2),
        })

    return result


def build_headways(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)

    for row in rows:
        key = (
            row.get("line_no"),
            row.get("service_type"),
            row.get("variant"),
            row.get("note"),
        )
        grouped[key].append(row)

    result = []

    for key, items in grouped.items():
        items.sort(key=lambda x: int(x["start_minutes"]))

        for i in range(len(items) - 1):
            a = items[i]
            b = items[i + 1]
            result.append({
                "line_no": a.get("line_no"),
                "service_type": a.get("service_type"),
                "variant": a.get("variant"),
                "note": a.get("note"),
                "from_start_time": a.get("start_time"),
                "to_start_time": b.get("start_time"),
                "headway_minutes": int(b["start_minutes"]) - int(a["start_minutes"]),
            })

    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--trips-csv", default="output/timetables/all_trips.csv")
    parser.add_argument("--out-dir", default="output/analytics")
    args = parser.parse_args()

    rows = load_csv(args.trips_csv)

    variant_stats = build_variant_stats(rows)
    headways = build_headways(rows)

    save_csv(variant_stats, Path(args.out_dir) / "variant_stats.csv")
    save_json(variant_stats, Path(args.out_dir) / "variant_stats.json")

    save_csv(headways, Path(args.out_dir) / "headways.csv")
    save_json(headways, Path(args.out_dir) / "headways.json")

    print("Analytics saved to", args.out_dir)


if __name__ == "__main__":
    main()