import csv
import json
from collections import Counter

print("=== all_trips.csv ===")
with open("output/timetables/all_trips.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("rows:", len(rows))
if rows:
    print("columns:", rows[0].keys())
    c = Counter(r.get("line_no", "") for r in rows)
    print("line_no counts:", c.most_common(20))

print("\n=== variant_stats.json ===")
with open("output/analytics/variant_stats.json", "r", encoding="utf-8") as f:
    stats = json.load(f)

print("rows:", len(stats))
print("sample:", stats[:10])