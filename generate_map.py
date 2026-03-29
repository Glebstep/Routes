"""
Generate an interactive HTML map from Heraklion bus data.

Preferred enriched inputs:
- output/lines_with_timetables.json
- output/routes_with_timetables.geojson

Fallback inputs:
- data/lines.json
- data/stops.json
- data/points/points_*.json

Run from project root:
    python3 generate_map.py

Open:
    output/map.html
"""

import json
import os
import glob


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_exists(path):
    return os.path.exists(path) and os.path.isfile(path)


def build_lines_lookup(lines):
    lines_map = {}

    for l in lines:
        line_code = str(l.get("code", "")).strip()
        if not line_code:
            continue

        color = l.get("color") or "#607D8B"
        if color in ("#787878", "#000000"):
            color = "#607D8B"

        if line_code == "91":
            color = "#e53935"
        elif line_code == "92":
            color = "#1e88e5"
        elif line_code == "93":
            color = "#43a047"

        line_entry = {
            "name": l.get("name", ""),
            "color": color,
            "routes": [],
            "timetable_stats": l.get("timetable_stats", []),
            "headways": l.get("timetable_headways", l.get("headways", [])),
        }

        for r in l.get("routes", []):
            route_entry = {
                "code": str(r.get("code", "")).strip(),
                "name": r.get("name", ""),
                "time": (
                    r.get("time")
                    or r.get("duration")
                    or r.get("travelTime")
                    or r.get("estimatedTime")
                ),
                "avg_trip_minutes": r.get("avg_trip_minutes"),
                "min_trip_minutes": r.get("min_trip_minutes"),
                "max_trip_minutes": r.get("max_trip_minutes"),
                "trip_count": r.get("trip_count"),
                "service_type": r.get("service_type"),
                "variant": r.get("variant"),
                "headway_minutes": r.get("headway_minutes"),
            }
            line_entry["routes"].append(route_entry)

        lines_map[line_code] = line_entry

    return lines_map


def build_stops_compact(stops):
    result = []
    for s in stops:
        result.append([
            round(float(s["latitude"]), 6),
            round(float(s["longitude"]), 6),
            s.get("name") or "",
            s.get("lineCodes", []),
        ])
    return result


def load_routes_from_geojson(geojson_path):
    data = load_json(geojson_path)
    routes = {}

    for feature in data.get("features", []):
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry", {}) or {}

        route_code = str(
            props.get("routeCode")
            or props.get("route_code")
            or props.get("code")
            or ""
        ).strip()

        if not route_code:
            continue

        geometry_type = geom.get("type")
        coordinates = geom.get("coordinates", [])

        coords = []
        if geometry_type == "LineString":
            coords = [[float(c[1]), float(c[0])] for c in coordinates if len(c) >= 2]
        elif geometry_type == "MultiLineString":
            for segment in coordinates:
                for c in segment:
                    if len(c) >= 2:
                        coords.append([float(c[1]), float(c[0])])

        if not coords:
            continue

        routes[route_code] = {
            "coords": coords,
            "line_code": str(
                props.get("lineCode")
                or props.get("line_code")
                or props.get("line")
                or ""
            ).strip(),
            "name": (
                props.get("name")
                or props.get("routeName")
                or props.get("route_name")
                or ""
            ),
            "variant": props.get("variant"),
            "service_type": props.get("service_type"),
            "trip_count": props.get("trip_count"),
            "avg_trip_minutes": props.get("avg_trip_minutes"),
            "min_trip_minutes": props.get("min_trip_minutes"),
            "max_trip_minutes": props.get("max_trip_minutes"),
            "headway_minutes": props.get("headway_minutes"),
            "timetable_stats": props.get("timetable_stats", []),
            "timetable_headways": props.get("timetable_headways", []),
            "raw_properties": props,
        }

    return routes


def load_routes_from_points():
    all_routes = {}
    for f in sorted(glob.glob("data/points/points_*.json")):
        for entry in load_json(f):
            rc = str(entry["routeCode"]).strip()
            coords = [
                [float(p["latitude"]), float(p["longitude"])]
                for p in sorted(entry["routePoints"], key=lambda x: x["sequence"])
            ]

            all_routes[rc] = {
                "coords": coords,
                "line_code": "",
                "name": "",
                "variant": None,
                "service_type": None,
                "trip_count": None,
                "avg_trip_minutes": None,
                "min_trip_minutes": None,
                "max_trip_minutes": None,
                "headway_minutes": None,
                "timetable_stats": [],
                "timetable_headways": [],
                "raw_properties": {},
            }
    return all_routes


def compact_routes(routes):
    routes_compact = {}
    for rc, route_data in routes.items():
        coords = route_data["coords"]

        if len(coords) > 300:
            step = max(1, len(coords) // 300)
            coords = coords[::step]
            if coords and coords[-1] != route_data["coords"][-1]:
                coords.append(route_data["coords"][-1])

        routes_compact[rc] = {
            "coords": [[round(c[0], 5), round(c[1], 5)] for c in coords],
            "line_code": route_data.get("line_code"),
            "name": route_data.get("name"),
            "variant": route_data.get("variant"),
            "service_type": route_data.get("service_type"),
            "trip_count": route_data.get("trip_count"),
            "avg_trip_minutes": route_data.get("avg_trip_minutes"),
            "min_trip_minutes": route_data.get("min_trip_minutes"),
            "max_trip_minutes": route_data.get("max_trip_minutes"),
            "headway_minutes": route_data.get("headway_minutes"),
            "timetable_stats": route_data.get("timetable_stats", []),
            "timetable_headways": route_data.get("timetable_headways", []),
        }

    return routes_compact


def attach_route_stats_from_geojson_to_lines(lines_map, routes_map):
    for line_code, line_data in lines_map.items():
        for r in line_data["routes"]:
            rc = r.get("code")
            if not rc or rc not in routes_map:
                continue

            rd = routes_map[rc]

            if not r.get("name") and rd.get("name"):
                r["name"] = rd["name"]
            if not r.get("variant") and rd.get("variant") is not None:
                r["variant"] = rd["variant"]
            if not r.get("service_type") and rd.get("service_type") is not None:
                r["service_type"] = rd["service_type"]
            if r.get("trip_count") is None and rd.get("trip_count") is not None:
                r["trip_count"] = rd["trip_count"]
            if r.get("avg_trip_minutes") is None and rd.get("avg_trip_minutes") is not None:
                r["avg_trip_minutes"] = rd["avg_trip_minutes"]
            if r.get("min_trip_minutes") is None and rd.get("min_trip_minutes") is not None:
                r["min_trip_minutes"] = rd["min_trip_minutes"]
            if r.get("max_trip_minutes") is None and rd.get("max_trip_minutes") is not None:
                r["max_trip_minutes"] = rd["max_trip_minutes"]
            if r.get("headway_minutes") is None and rd.get("headway_minutes") is not None:
                r["headway_minutes"] = rd["headway_minutes"]


def main():
    lines_path = (
        "output/lines_with_timetables.json"
        if file_exists("output/lines_with_timetables.json")
        else "data/lines.json"
    )
    stops_path = "data/stops.json"
    use_enriched_geo = file_exists("output/routes_with_timetables.geojson")

    lines = load_json(lines_path)
    stops = load_json(stops_path)

    lines_map = build_lines_lookup(lines)
    stops_compact = build_stops_compact(stops)

    if use_enriched_geo:
        all_routes = load_routes_from_geojson("output/routes_with_timetables.geojson")
    else:
        all_routes = load_routes_from_points()

    attach_route_stats_from_geojson_to_lines(lines_map, all_routes)
    routes_compact = compact_routes(all_routes)

    route_to_line = {}
    for lc, ldata in lines_map.items():
        for r in ldata["routes"]:
            route_to_line[r["code"]] = lc

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Heraklion City Bus Map</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
#map {{ width: 100%; height: 100vh; }}

.controls {{
    position: absolute;
    top: 10px;
    left: 60px;
    z-index: 1000;
    background: white;
    border-radius: 10px;
    padding: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    max-height: 90vh;
    overflow-y: auto;
    min-width: 280px;
    max-width: 520px;
}}

.controls h3 {{
    margin: 0 0 8px;
    font-size: 14px;
}}

.line-btn {{
    display: inline-block;
    padding: 4px 10px;
    margin: 2px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: 2px solid transparent;
    color: white;
    opacity: 0.5;
    transition: all 0.2s;
    user-select: none;
}}

.line-btn.active {{
    opacity: 1;
    border-color: #333;
    transform: scale(1.05);
}}

.line-btn:hover {{
    opacity: 0.85;
}}

.ctrl-buttons {{
    margin-top: 8px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}}

.ctrl-buttons button {{
    font-size: 12px;
    padding: 5px 12px;
    cursor: pointer;
    border: 1px solid #ccc;
    border-radius: 6px;
    background: #f5f5f5;
}}

#stats {{
    font-size: 12px;
    color: #666;
    margin-top: 10px;
    line-height: 1.4;
}}

.leaflet-popup-content {{
    font-size: 13px;
    line-height: 1.45;
    min-width: 230px;
}}

.leaflet-popup-content b {{
    color: #333;
}}

.popup-row {{
    margin-top: 4px;
}}
</style>
</head>
<body>
<div id="map"></div>

<div class="controls">
    <h3>Heraklion Bus Lines</h3>
    <div id="line-buttons"></div>

    <div class="ctrl-buttons">
        <button onclick="showAll()">Show all</button>
        <button onclick="hideAll()">Hide all</button>
    </div>

    <div id="stats"></div>
</div>

<script>
const LINES = {json.dumps(lines_map, ensure_ascii=False)};
const STOPS = {json.dumps(stops_compact, ensure_ascii=False)};
const ROUTES = {json.dumps(routes_compact, ensure_ascii=False)};
const R2L = {json.dumps(route_to_line, ensure_ascii=False)};

const map = L.map('map').setView([35.3350, 25.1340], 13);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png', {{
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19
}}).addTo(map);

const activeLayers = {{}};
const activeLines = new Set();

function escapeHtml(text) {{
    return String(text ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}}

function fmtMinutes(value) {{
    if (value === null || value === undefined || value === '') return 'нет данных';
    const n = Number(value);
    return Number.isFinite(n) ? (Math.round(n * 10) / 10) + ' min' : String(value);
}}

function getLineColor(lineCode) {{
    return LINES[lineCode] ? LINES[lineCode].color : '#999';
}}

function toggleLine(lineCode) {{
    if (activeLines.has(lineCode)) {{
        activeLines.delete(lineCode);
        if (activeLayers[lineCode]) {{
            activeLayers[lineCode].forEach(layer => map.removeLayer(layer));
            delete activeLayers[lineCode];
        }}
    }} else {{
        activeLines.add(lineCode);
        drawLine(lineCode);
    }}
    updateButtons();
    updateStats();
}}

function buildRoutePopup(lineCode, route) {{
    const routeData = ROUTES[route.code] || {{}};
    const lineData = LINES[lineCode] || {{}};

    let routeStat = null;
    if (routeData.timetable_stats && routeData.timetable_stats.length) {{
        routeStat = routeData.timetable_stats[0];
    }}

    let lineStat = null;
    if (lineData.timetable_stats && lineData.timetable_stats.length) {{
        lineStat = lineData.timetable_stats[0];
    }}

    let routeHeadway = null;
    if (routeData.timetable_headways && routeData.timetable_headways.length) {{
        routeHeadway = routeData.timetable_headways[0];
    }}

    let lineHeadway = null;
    if (lineData.headways && lineData.headways.length) {{
        lineHeadway = lineData.headways[0];
    }}

    const statSource = routeStat || lineStat || null;
    const headwaySource = routeHeadway || lineHeadway || null;

    const name = route.name || routeData.name || 'Unnamed';
    const variant =
        route.variant ||
        routeData.variant ||
        (statSource ? statSource.variant : '') ||
        '';
    const serviceType =
        route.service_type ||
        routeData.service_type ||
        (statSource ? statSource.service_type : '') ||
        '';
    const tripCount =
        route.trip_count ??
        routeData.trip_count ??
        (statSource ? statSource.trip_count : null);
    const avgTrip =
        route.avg_trip_minutes ??
        routeData.avg_trip_minutes ??
        (statSource ? statSource.avg_trip_minutes : null);
    const minTrip =
        route.min_trip_minutes ??
        routeData.min_trip_minutes ??
        (statSource ? statSource.min_trip_minutes : null);
    const maxTrip =
        route.max_trip_minutes ??
        routeData.max_trip_minutes ??
        (statSource ? statSource.max_trip_minutes : null);
    const headway =
        route.headway_minutes ??
        routeData.headway_minutes ??
        (headwaySource ? (headwaySource.avg_headway_minutes ?? headwaySource.headway_minutes) : null);

    const rawTime = route.time || '';
    const sourceLabel = routeStat ? 'route' : (lineStat ? 'line fallback' : 'none');

    let html = '';
    html += '<b>Line ' + escapeHtml(lineCode) + '</b><br>';
    html += '<div class="popup-row">Route: ' + escapeHtml(name) + '</div>';
    html += '<div class="popup-row">Route code: ' + escapeHtml(route.code || '-') + '</div>';

    if (variant) {{
        html += '<div class="popup-row">Variant: ' + escapeHtml(variant) + '</div>';
    }}

    if (serviceType) {{
        html += '<div class="popup-row">Service: ' + escapeHtml(serviceType) + '</div>';
    }}

    if (rawTime) {{
        html += '<div class="popup-row">Time: ' + escapeHtml(rawTime) + '</div>';
    }}

    html += '<div class="popup-row">Avg trip: ' + escapeHtml(fmtMinutes(avgTrip)) + '</div>';
    html += '<div class="popup-row">Min trip: ' + escapeHtml(fmtMinutes(minTrip)) + '</div>';
    html += '<div class="popup-row">Max trip: ' + escapeHtml(fmtMinutes(maxTrip)) + '</div>';
    html += '<div class="popup-row">Headway: ' + escapeHtml(fmtMinutes(headway)) + '</div>';
    html += '<div class="popup-row">Trips: ' + escapeHtml(tripCount ?? 'нет данных') + '</div>';

    if (sourceLabel !== 'none') {{
        html += '<div class="popup-row" style="color:#666;font-size:12px;">Stats source: ' + escapeHtml(sourceLabel) + '</div>';
    }}

    return html;
}}

function drawLine(lineCode) {{
    if (activeLayers[lineCode]) {{
        activeLayers[lineCode].forEach(layer => map.removeLayer(layer));
    }}

    activeLayers[lineCode] = [];
    const color = getLineColor(lineCode);
    const lineData = LINES[lineCode];
    if (!lineData) return;

    lineData.routes.forEach(route => {{
        const routeData = ROUTES[route.code];
        if (routeData && routeData.coords && routeData.coords.length > 1) {{
            const popupHtml = buildRoutePopup(lineCode, route);

            const clickLine = L.polyline(routeData.coords, {{
                color: color,
                weight: 14,
                opacity: 0.01
            }}).addTo(map);

            const visibleLine = L.polyline(routeData.coords, {{
                color: color,
                weight: 4,
                opacity: 0.85
            }}).addTo(map);

            clickLine.bindPopup(popupHtml);
            visibleLine.bindPopup(popupHtml);

            activeLayers[lineCode].push(clickLine);
            activeLayers[lineCode].push(visibleLine);
        }}
    }});

    STOPS.forEach(s => {{
        const stopLat = s[0];
        const stopLng = s[1];
        const stopName = s[2];
        const stopLines = s[3] || [];

        if (stopLines.includes(lineCode)) {{
            const marker = L.circleMarker([stopLat, stopLng], {{
                radius: 5,
                fillColor: color,
                color: '#fff',
                weight: 1.5,
                fillOpacity: 0.9
            }}).addTo(map);

            marker.bindPopup(
                '<b>' + escapeHtml(stopName || 'Stop') + '</b><br>' +
                'Lines: ' + escapeHtml(stopLines.join(', '))
            );

            activeLayers[lineCode].push(marker);
        }}
    }});
}}

function showAll() {{
    Object.keys(LINES).forEach(lc => {{
        if (!activeLines.has(lc) && LINES[lc].routes.length > 0) {{
            toggleLine(lc);
        }}
    }});
}}

function hideAll() {{
    [...activeLines].forEach(lc => toggleLine(lc));
}}

function updateButtons() {{
    document.querySelectorAll('.line-btn').forEach(btn => {{
        btn.classList.toggle('active', activeLines.has(btn.dataset.line));
    }});
}}

function updateStats() {{
    const stopsSet = new Set();

    STOPS.forEach(s => {{
        const stopLines = s[3] || [];
        for (const lc of stopLines) {{
            if (activeLines.has(lc)) {{
                stopsSet.add(s[0] + ',' + s[1]);
                break;
            }}
        }}
    }});

    let routeCount = 0;
    activeLines.forEach(lc => {{
        routeCount += (LINES[lc]?.routes?.length || 0);
    }});

    document.getElementById('stats').textContent =
        activeLines.size + ' lines, ' +
        routeCount + ' routes, ' +
        stopsSet.size + ' stops';
}}

const container = document.getElementById('line-buttons');
Object.entries(LINES)
    .sort((a, b) => a[0].localeCompare(b[0], undefined, {{ numeric: true }}))
    .forEach(([code, data]) => {{
        if (!data.routes || data.routes.length === 0) return;

        const btn = document.createElement('span');
        btn.className = 'line-btn';
        btn.dataset.line = code;
        btn.style.background = data.color;
        btn.textContent = code;
        btn.title = data.name || code;
        btn.onclick = () => toggleLine(code);
        container.appendChild(btn);
    }});

['02', '06', '10', '12'].forEach(lc => {{
    if (LINES[lc] && LINES[lc].routes.length > 0) {{
        toggleLine(lc);
    }}
}});
</script>
</body>
</html>"""

    os.makedirs("output", exist_ok=True)
    with open("output/map.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Map generated: output/map.html")
    print(f"  {len(lines_map)} lines, {len(stops_compact)} stops, {len(routes_compact)} route geometries")
    print(f"  lines source: {lines_path}")
    print(f"  routes source: {'output/routes_with_timetables.geojson' if use_enriched_geo else 'data/points/points_*.json'}")
    print("  Open in browser to explore!")


if __name__ == "__main__":
    main()