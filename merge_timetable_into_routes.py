from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def normalize_line_no(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    digits = "".join(ch for ch in s if ch.isdigit())
    return digits.zfill(2) if digits else s


def extract_line_key_from_line(line: dict) -> str:
    candidates = [
        line.get("line_no"),
        line.get("lineNo"),
        line.get("line"),
        line.get("id"),
        line.get("name"),
        line.get("number"),
        line.get("code"),
    ]
    for c in candidates:
        key = normalize_line_no(c)
        if key:
            return key
    return ""


def extract_line_key_from_feature(props: dict) -> str:
    candidates = [
        props.get("line_no"),
        props.get("lineNo"),
        props.get("line"),
        props.get("route_short_name"),
        props.get("route_id"),
        props.get("id"),
        props.get("name"),
        props.get("number"),
        props.get("code"),
    ]
    for c in candidates:
        key = normalize_line_no(c)
        if key:
            return key
    return ""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--routes", default="output/routes.geojson")
    parser.add_argument("--lines", default="output/lines_with_timetables.json")
    parser.add_argument("--out", default="output/routes_with_timetables.geojson")
    args = parser.parse_args()

    routes_geojson = load_json(args.routes)
    lines = load_json(args.lines)

    lines_by_no = {}
    for line in lines:
        key = extract_line_key_from_line(line)
        if not key:
            continue

        lines_by_no[key] = {
            "timetable_stats": line.get("timetable_stats", []),
            "timetable_headways": line.get("timetable_headways", []),
        }

    for feature in routes_geojson.get("features", []):
        props = feature.setdefault("properties", {})
        key = extract_line_key_from_feature(props)

        timetable = lines_by_no.get(key, {})
        props["timetable_stats"] = timetable.get("timetable_stats", [])
        props["timetable_headways"] = timetable.get("timetable_headways", [])

    save_json(routes_geojson, args.out)
    print("Saved:", args.out)


if __name__ == "__main__":
    main()