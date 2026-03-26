"""
Heraklion City Bus Data Processor
Loads lines, stops, and route points from JSON files.
Structures, filters, and exports the data.
"""
 
import json
import os
import glob
from collections import defaultdict
 
 
# ── Data Loading ──────────────────────────────────────────────
 
def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
 
 
def load_all_points(points_dir):
    """Load all points_*.json files and merge into {routeCode: [points]}"""
    all_routes = {}
    files = sorted(glob.glob(os.path.join(points_dir, "points_*.json")))
    print(f"  Found {len(files)} points files")
    for f in files:
        data = load_json(f)
        for entry in data:
            route_code = entry["routeCode"]
            points = entry["routePoints"]
            all_routes[route_code] = points
    print(f"  Loaded {len(all_routes)} route geometries")
    return all_routes
 
 
def load_data(data_dir="data"):
    """Load all data from the data directory."""
    print("Loading data...")
    lines = load_json(os.path.join(data_dir, "lines.json"))
    print(f"  Lines: {len(lines)}")
    
    stops = load_json(os.path.join(data_dir, "stops.json"))
    print(f"  Stops: {len(stops)}")
    
    points = load_all_points(os.path.join(data_dir, "points"))
    print()
    return lines, stops, points
 
 
# ── Data Structuring ──────────────────────────────────────────
 
def build_structured_data(lines, stops, points):
    """
    Build a unified data structure:
    {
      line_code: {
        "info": {name, color, ...},
        "routes": {
          route_code: {
            "name": ...,
            "stops": [...],
            "geometry": [lat/lng points]
          }
        }
      }
    }
    """
    # Index stops by route code
    stops_by_route = defaultdict(list)
    for stop in stops:
        for rc in stop.get("routeCodes", []):
            stops_by_route[rc].append({
                "code": stop["code"],
                "name": stop.get("name"),
                "lat": stop["latitude"],
                "lng": stop["longitude"],
            })
 
    structured = {}
    for line in lines:
        line_code = line["code"]
        line_data = {
            "info": {
                "id": line["id"],
                "code": line_code,
                "name": line["name"],
                "color": line["color"],
                "textColor": line.get("textColor"),
                "borderColor": line.get("borderColor"),
            },
            "routes": {}
        }
        for route in line.get("routes", []):
            rc = route["code"]
            route_data = {
                "name": route["name"],
                "direction": route.get("direction"),
                "stops": stops_by_route.get(rc, []),
                "geometry": points.get(rc, []),
            }
            line_data["routes"][rc] = route_data
        structured[line_code] = line_data
 
    return structured
 
 
# ── Filtering ─────────────────────────────────────────────────
 
def filter_by_line(structured, line_code):
    """Get all data for a specific line (e.g., '01', '09')."""
    return structured.get(line_code)
 
 
def filter_by_stop_name(stops, query):
    """Search stops by name (case-insensitive partial match)."""
    query_lower = query.lower()
    return [s for s in stops if s.get("name") and query_lower in s["name"].lower()]
 
 
def find_lines_for_stop(stops, stop_code):
    """Find which lines pass through a given stop."""
    for s in stops:
        if s["code"] == stop_code:
            return {
                "stop": s.get("name"),
                "lines": s.get("lineCodes", []),
                "routes": s.get("routeCodes", []),
            }
    return None
 
 
def get_active_lines(lines):
    """Get lines that have at least one route."""
    return [l for l in lines if len(l.get("routes", [])) > 0]
 
 
def get_inactive_lines(lines):
    """Get lines with no routes."""
    return [l for l in lines if len(l.get("routes", [])) == 0]
 
 
# ── Stats & Summary ───────────────────────────────────────────
 
def print_summary(lines, stops, points, structured):
    print("=" * 60)
    print("HERAKLION CITY BUS - DATA SUMMARY")
    print("=" * 60)
 
    active = get_active_lines(lines)
    inactive = get_inactive_lines(lines)
 
    print(f"\nLines: {len(lines)} total ({len(active)} active, {len(inactive)} inactive)")
    if inactive:
        print(f"  Inactive: {', '.join(l['code'] + ' (' + l['name'] + ')' for l in inactive)}")
 
    total_routes = sum(len(l.get("routes", [])) for l in lines)
    print(f"Routes: {total_routes} total")
    print(f"Stops: {len(stops)} total")
    print(f"Route geometries: {len(points)} loaded")
 
    # Stops with no name
    unnamed = [s for s in stops if not s.get("name")]
    print(f"Unnamed stops: {len(unnamed)}")
 
    print("\n" + "-" * 60)
    print("LINES OVERVIEW:")
    print("-" * 60)
    print(f"{'Code':<6} {'Name':<45} {'Routes':<8} {'Color'}")
    print("-" * 60)
    for line in sorted(lines, key=lambda x: x["code"]):
        n_routes = len(line.get("routes", []))
        marker = "  " if n_routes > 0 else "❌"
        print(f"{marker} {line['code']:<4} {line['name']:<45} {n_routes:<8} {line['color']}")
 
    # Per-line stop counts
    print("\n" + "-" * 60)
    print("STOPS PER LINE:")
    print("-" * 60)
    for line_code in sorted(structured.keys()):
        line_info = structured[line_code]["info"]
        all_stops = set()
        for route in structured[line_code]["routes"].values():
            for s in route["stops"]:
                all_stops.add(s["code"])
        if all_stops:
            print(f"  Line {line_code} ({line_info['name']}): {len(all_stops)} stops")
 
 
# ── Export ────────────────────────────────────────────────────
 
def export_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported: {filepath}")
 
 
def export_structured(structured, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Full structured export
    export_json(structured, os.path.join(output_dir, "structured_all.json"))
 
    # Per-line exports
    lines_dir = os.path.join(output_dir, "lines")
    os.makedirs(lines_dir, exist_ok=True)
    for line_code, data in structured.items():
        export_json(data, os.path.join(lines_dir, f"line_{line_code}.json"))
    
    print(f"Exported {len(structured)} individual line files to {lines_dir}/")
 
 
def export_stops_csv(stops, filepath):
    """Export stops to CSV for easy viewing."""
    import csv
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "name", "latitude", "longitude", "lines", "routes"])
        for s in sorted(stops, key=lambda x: x.get("name") or ""):
            writer.writerow([
                s["code"],
                s.get("name") or "",
                s["latitude"],
                s["longitude"],
                ";".join(s.get("lineCodes", [])),
                ";".join(s.get("routeCodes", [])),
            ])
    print(f"Exported: {filepath}")
 
 
def export_geojson(structured, filepath):
    """Export all route geometries as GeoJSON for map visualization."""
    features = []
    for line_code, line_data in structured.items():
        info = line_data["info"]
        for route_code, route in line_data["routes"].items():
            if not route["geometry"]:
                continue
            coords = [
                [float(p["longitude"]), float(p["latitude"])]
                for p in sorted(route["geometry"], key=lambda x: x["sequence"])
            ]
            feature = {
                "type": "Feature",
                "properties": {
                    "line_code": line_code,
                    "line_name": info["name"],
                    "route_code": route_code,
                    "route_name": route["name"],
                    "color": info["color"],
                    "stops_count": len(route["stops"]),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                }
            }
            features.append(feature)
 
    # Add stops as points
    for line_code, line_data in structured.items():
        info = line_data["info"]
        seen = set()
        for route in line_data["routes"].values():
            for stop in route["stops"]:
                if stop["code"] in seen:
                    continue
                seen.add(stop["code"])
                features.append({
                    "type": "Feature",
                    "properties": {
                        "type": "stop",
                        "code": stop["code"],
                        "name": stop["name"],
                        "line_code": line_code,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [stop["lng"], stop["lat"]],
                    }
                })
 
    geojson = {"type": "FeatureCollection", "features": features}
    export_json(geojson, filepath)
 
 
# ── Main ──────────────────────────────────────────────────────
 
def main():
    lines, stops, points = load_data("data")
    structured = build_structured_data(lines, stops, points)
 
    # Summary
    print_summary(lines, stops, points, structured)
 
    # Export all
    print("\n" + "=" * 60)
    print("EXPORTING...")
    print("=" * 60)
    export_structured(structured, "output")
    export_stops_csv(stops, "output/stops.csv")
    export_geojson(structured, "output/routes.geojson")
 
    # Example filters
    print("\n" + "=" * 60)
    print("EXAMPLE QUERIES")
    print("=" * 60)
 
    # Search stops by name
    print("\n Stops containing 'AIRPORT':")
    for s in filter_by_stop_name(stops, "airport")[:5]:
        print(f"  {s['code']} - {s['name']} ({s['latitude']}, {s['longitude']})")
 
    # Find lines for a stop
    print("\n Lines passing through stop 0022 (TS PORT):")
    result = find_lines_for_stop(stops, "0022")
    if result:
        print(f"  Stop: {result['stop']}")
        print(f"  Lines: {', '.join(result['lines'])}")
 
    # Line details
    print("\n Line 93 (Green LINE):")
    line93 = filter_by_line(structured, "93")
    if line93:
        print(f"  Name: {line93['info']['name']}")
        for rc, route in line93["routes"].items():
            print(f"  Route {rc}: {route['name']}")
            print(f"    Stops: {len(route['stops'])}, Geometry points: {len(route['geometry'])}")
 
 
if __name__ == "__main__":
    main()