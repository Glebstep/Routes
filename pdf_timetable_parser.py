from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import pdfplumber


TIME_RE = r"([0-2]?\d:\d{2})"
ROW_RE = re.compile(
    rf"^\s*(?:(?P<idx>\d+)\s+)?(?P<route>.+?)\s+{TIME_RE}\s+{TIME_RE}(?:\s+(?P<line>\d+))?\s*$"
)


@dataclass
class TripRecord:
    trip_index: Optional[int]
    line_no: Optional[str]
    route_text_raw: str
    variant: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    note: Optional[str]
    start_time: str
    terminal_time: str
    start_minutes: int
    terminal_minutes: int
    trip_minutes: int
    service_type: str
    source_pdf: str
    source_page: int


def normalize_space(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def hhmm_to_minutes(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def normalize_time_str(value: str) -> str:
    h, m = value.split(":")
    return f"{int(h):02d}:{int(m):02d}"


def adjust_rollover(start_min: int, end_min: int) -> int:
    if end_min < start_min:
        end_min += 24 * 60
    return end_min


def detect_service_type(text: str) -> str:
    low = text.lower()
    if "daily" in low or "καθημεριν" in low:
        return "daily"
    if "saturday" in low:
        return "saturday"
    if "sunday" in low or "holiday" in low:
        return "sunday_holiday"
    return "unknown"


def clean_route_text(route: str) -> str:
    route = normalize_space(route)
    route = route.strip("- ").strip()
    return route


def split_route_parts(route: str):
    note = None

    m = re.search(r"\(([^)]+)\)", route)
    if m:
        note = m.group(1).strip()
        route = re.sub(r"\([^)]+\)", "", route).strip()

    parts = [p.strip(" -") for p in route.split(" - ") if p.strip(" -")]
    if not parts:
        return None, None, None, note

    origin = parts[0] if len(parts) >= 1 else None
    destination = parts[-1] if len(parts) >= 2 else None

    variant = None
    if len(parts) >= 3:
        variant = " / ".join(parts[1:-1])
    elif len(parts) == 2:
        variant = parts[1]

    return origin, variant, destination, note


def is_probably_data_row(line: str) -> bool:
    if not re.search(TIME_RE, line):
        return False

    low = line.lower()
    bad_markers = [
        "address:",
        "fax",
        "e-mail",
        "contact phone",
        "heraklion city bus",
        "departures",
        "returns",
        "itineraries",
        "routes -",
        "start from",
        "traffic office",
        "info@",
        "http://",
    ]
    return not any(marker in low for marker in bad_markers)


def parse_row(line: str, service_type: str, source_pdf: str, source_page: int) -> Optional[TripRecord]:
    line = normalize_space(line)
    if not is_probably_data_row(line):
        return None

    m = ROW_RE.match(line)
    if not m:
        return None

    trip_index = int(m.group("idx")) if m.group("idx") else None
    route_text_raw = clean_route_text(m.group("route"))
    start_time = normalize_time_str(m.group(3))
    terminal_time = normalize_time_str(m.group(4))
    line_no = m.group("line")

    origin, variant, destination, note = split_route_parts(route_text_raw)

    start_minutes = hhmm_to_minutes(start_time)
    terminal_minutes = hhmm_to_minutes(terminal_time)
    terminal_minutes = adjust_rollover(start_minutes, terminal_minutes)
    trip_minutes = terminal_minutes - start_minutes

    return TripRecord(
        trip_index=trip_index,
        line_no=line_no.zfill(2) if line_no else None,
        route_text_raw=route_text_raw,
        variant=variant,
        origin=origin,
        destination=destination,
        note=note,
        start_time=start_time,
        terminal_time=terminal_time,
        start_minutes=start_minutes,
        terminal_minutes=terminal_minutes,
        trip_minutes=trip_minutes,
        service_type=service_type,
        source_pdf=source_pdf,
        source_page=source_page,
    )


def infer_line_no_from_filename(filename: str) -> Optional[str]:
    m = re.search(r"(\d+)", filename)
    if not m:
        return None
    return m.group(1).zfill(2)


def parse_pdf_timetable(pdf_path: str | Path) -> List[TripRecord]:
    pdf_path = Path(pdf_path)
    records: List[TripRecord] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = normalize_space(text)
            if not text:
                continue

            service_type = detect_service_type(text)

            for raw_line in text.splitlines():
                rec = parse_row(
                    line=raw_line,
                    service_type=service_type,
                    source_pdf=pdf_path.name,
                    source_page=page_num,
                )
                if rec:
                    records.append(rec)

    inferred_line = infer_line_no_from_filename(pdf_path.name)
    for r in records:
        if not r.line_no and inferred_line:
            r.line_no = inferred_line

    return records


def save_json(records: List[TripRecord], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)


def save_csv(records: List[TripRecord], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [asdict(r) for r in records]
    if not rows:
        return

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)