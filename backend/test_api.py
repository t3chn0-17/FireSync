"""Run with the API server stopped or running: python test_api.py"""
from fastapi.testclient import TestClient
import api

c = TestClient(api.app)
def get(url, code=200):
    r = c.get(url); assert r.status_code == code, (url, r.status_code, r.text[:200]); return r.json()

h = get("/health"); assert h["status"] == "ok" and h["data_available"]
o = get("/api/overview"); print("overview:", {k: o[k] for k in ("total_observations","unique_grid_cells","sensors","platforms","date_range","valid_records","rejected_records")})
assert o["total_observations"] == 1282 and o["unique_grid_cells"] == 449 and o["sensors"] == 2 and o["platforms"] == 4

g = get("/api/hotspots/geojson"); assert g["type"] == "FeatureCollection" and len(g["features"]) == 1282
for f in g["features"]:
    lon, lat = f["geometry"]["coordinates"]
    assert 24 <= lon <= 37 and 21 <= lat <= 33, f["geometry"]   # Egypt bbox, WGS84 lon/lat order
    assert isinstance(f["properties"]["frp"], float) and f["properties"]["platform"] and f["properties"]["sensor"]
print("geojson OK, all 1282 features inside Egypt bbox in [lon,lat]")

from collections import Counter
print("by platform:", dict(Counter(f["properties"]["platform"] for f in g["features"])))
print("by satellite:", dict(Counter(f["properties"]["satellite_name"] for f in g["features"])))

# filters
assert get("/api/hotspots/geojson?sensor=MODIS")["metadata"]["total_matching"] == 33
assert get("/api/hotspots/geojson?platform=VIIRS_NOAA21")["metadata"]["total_matching"] == 645
assert get("/api/hotspots/geojson?satellite=Aqua")["metadata"]["total_matching"] == 6
assert get("/api/hotspots/geojson?satellite=Terra")["metadata"]["total_matching"] == 27
assert get("/api/hotspots/geojson?satellite=NOAA-20")["metadata"]["total_matching"] == 505
assert get("/api/hotspots/geojson?satellite=SNPP")["metadata"]["total_matching"] == 99
d1 = get("/api/hotspots/geojson?start_date=2026-11-02&end_date=2026-11-02")["metadata"]["total_matching"]; assert d1 == 284, d1
mf = get("/api/hotspots/geojson?min_frp=10")["features"]; assert all(f["properties"]["frp"] >= 10 for f in mf)
print("filters OK; min_frp=10 ->", len(mf), "| 2026-11-02 ->", d1)
assert len(get("/api/hotspots/geojson?limit=10")["features"]) == 10
get("/api/observations?start_date=bad", 400)

ob = get("/api/observations?limit=3"); assert ob["total"] == 1282 and ob["count"] == 3
oid = ob["observations"][0]["observation_id"]; assert get(f"/api/observations/{oid}")["observation_id"] == oid
get("/api/observations/nope", 404)
hz = get("/api/harmonization?limit=100000".replace("100000","20000")); print("harmonization rows:", hz["total"]); assert hz["total"] == 1010
assert sum(r["observation_count"] for r in hz["rows"]) == 1282
assert get("/api/harmonization?platform=MODIS")["total"] > 0
st = get("/api/statistics"); print("stats platforms:", [(p["platform"], p["observations"], p["unique_grid_cells"]) for p in st["by_platform"]])
print("stats satellites:", [(p["satellite"], p["observations"]) for p in st["by_satellite"]], "day/night:", st["day_night"])
gid = g["features"][0]["properties"]["grid_id"]; gc = get(f"/api/grid/{gid}"); print("grid", gid, gc["observation_count"], gc["center"])
get("/api/grid/0_0", 404)
cors = c.options("/api/overview", headers={"Origin": "http://192.168.1.77:5173", "Access-Control-Request-Method": "GET"})
print("CORS preflight:", cors.status_code, cors.headers.get("access-control-allow-origin"))
print("ALL TESTS PASSED")
