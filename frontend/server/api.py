"""FireSync API — serves processed NASA FIRMS data (no mock data)."""
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

try:  # optional .env support without extra dependency
    for line in (BASE_DIR / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
except FileNotFoundError:
    pass

MAX_LIMIT = int(os.getenv("FIRESYNC_MAX_LIMIT", "20000"))
DEFAULT_LIMIT = int(os.getenv("FIRESYNC_DEFAULT_LIMIT", "5000"))
CORS_ORIGINS = [o.strip() for o in os.getenv("FIRESYNC_CORS_ORIGINS", "*").split(",") if o.strip()]

SATELLITE_NAMES = {"Terra": "Terra", "Aqua": "Aqua", "SNPP": "Suomi-NPP", "N20": "NOAA-20", "N21": "NOAA-21"}
DISCLAIMER = ("FireSync is a prototype comparing NASA FIRMS active-fire observations from different "
              "sensors. FRP is never summed across sensors; confidence values are original and not "
              "comparable between MODIS and VIIRS. Not validated or endorsed by NASA.")

app = FastAPI(title="FireSync API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"],
                   allow_credentials=False)

STATE = {"obs": pd.DataFrame(), "daily": pd.DataFrame(), "spatial": pd.DataFrame(), "stats": {}, "integrity": {}}


def load_data() -> None:
    def rd(name, **kw):
        p = OUTPUT_DIR / name
        if not p.exists() or p.stat().st_size < 5:
            return pd.DataFrame()
        return pd.read_csv(p, **kw)

    obs = rd("observations_indexed.csv", dtype={"acq_time": str, "confidence": str, "grid_id": str})
    if not obs.empty:
        obs["acq_time"] = obs["acq_time"].str.zfill(4)
        obs["acq_datetime"] = pd.to_datetime(obs["acq_datetime"], utc=True)
        obs["date"] = obs["acq_datetime"].dt.strftime("%Y-%m-%d")
        obs["satellite_name"] = obs["satellite"].map(SATELLITE_NAMES).fillna(obs["satellite"])
    STATE["obs"] = obs
    STATE["daily"] = rd("harmonized_daily.csv", dtype={"grid_id": str})
    STATE["spatial"] = rd("spatial_summary.csv", dtype={"grid_id": str})
    for key, name in (("stats", "platform_statistics.json"), ("integrity", "integrity_report.json")):
        p = OUTPUT_DIR / name
        STATE[key] = json.loads(p.read_text()) if p.exists() else {}


load_data()


def clean(v):
    """JSON-safe scalar: NaN -> None, numpy -> python."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if v is pd.NA or v is pd.NaT:
        return None
    return v


def obs_properties(r) -> dict:
    return {
        "observation_id": r["observation_id"], "grid_id": r["grid_id"],
        "sensor": r["sensor"], "platform": r["platform"],
        "satellite": r["satellite"], "satellite_name": r["satellite_name"],
        "frp": clean(r["frp"]), "brightness": clean(r["brightness"]), "bright_t31": clean(r["bright_t31"]),
        "confidence": clean(r["confidence"]),  # original value; MODIS numeric vs VIIRS l/n/h
        "daynight": clean(r["daynight"]), "scan": clean(r["scan"]), "track": clean(r["track"]),
        "acq_date": r["date"], "acq_time": r["acq_time"],
        "acq_datetime": r["acq_datetime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": float(r["latitude"]), "longitude": float(r["longitude"]),
        "source_file": r["source_file"],
    }


def filter_df(df, start_date=None, end_date=None, sensor=None, platform=None, satellite=None,
              min_frp=None, max_frp=None):
    if df.empty:
        return df
    m = pd.Series(True, index=df.index)
    dcol = "date"
    if start_date:
        m &= df[dcol] >= start_date
    if end_date:
        m &= df[dcol] <= end_date
    if sensor:
        m &= df["sensor"].str.upper().isin([s.strip().upper() for s in sensor.split(",")])
    if platform:
        m &= df["platform"].str.upper().isin([s.strip().upper() for s in platform.split(",")])
    if satellite:  # accepts Terra/Aqua/SNPP/N20/N21 or Suomi-NPP/NOAA-20/NOAA-21
        wanted = [s.strip().upper() for s in satellite.split(",")]
        if "satellite_name" in df.columns:
            m &= df["satellite"].str.upper().isin(wanted) | df["satellite_name"].str.upper().isin(wanted)
    if min_frp is not None and "frp" in df.columns:
        m &= df["frp"] >= min_frp
    if max_frp is not None and "frp" in df.columns:
        m &= df["frp"] <= max_frp
    return df[m]


def check_dates(start_date, end_date):
    for d in (start_date, end_date):
        if d:
            try:
                pd.Timestamp(d)
            except Exception:
                raise HTTPException(400, f"Invalid date '{d}', expected YYYY-MM-DD")
            if len(d) != 10:
                raise HTTPException(400, f"Invalid date '{d}', expected YYYY-MM-DD")


@app.get("/health")
def health():
    ok = not STATE["obs"].empty
    return {"status": "ok", "data_available": ok,
            "datasets": {k: (not STATE[k].empty) for k in ("obs", "daily", "spatial")},
            "message": None if ok else "No processed data. Run pipeline.py then harmonization.py."}


@app.post("/api/reload")
def reload_data():
    load_data()
    return health()


@app.get("/api/overview")
def overview():
    obs = STATE["obs"]
    if obs.empty:
        return {"total_observations": 0, "unique_grid_cells": 0, "sensors": 0, "platforms": 0,
                "date_range": None, "valid_records": 0, "rejected_records": 0, "disclaimer": DISCLAIMER}
    integ = STATE["integrity"]
    return {
        "total_observations": int(len(obs)),
        "unique_grid_cells": int(obs["grid_id"].nunique()),  # grid cells, NOT unique fires
        "sensors": int(obs["sensor"].nunique()), "platforms": int(obs["platform"].nunique()),
        "satellites": int(obs["satellite"].nunique()),
        "sensor_list": sorted(obs["sensor"].unique().tolist()),
        "platform_list": sorted(obs["platform"].unique().tolist()),
        "satellite_list": sorted(obs["satellite"].unique().tolist()),
        "date_range": {"start": obs["date"].min(), "end": obs["date"].max()},
        "valid_records": integ.get("valid_records", int(len(obs))),
        "rejected_records": integ.get("rejected_records"),
        "grid_size_km": 1.0, "grid_crs": "EPSG:6933", "region": "Egypt",
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/observations")
def observations(start_date: Optional[str] = None, end_date: Optional[str] = None,
                 sensor: Optional[str] = None, platform: Optional[str] = None,
                 satellite: Optional[str] = None, min_frp: Optional[float] = None,
                 max_frp: Optional[float] = None,
                 limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0)):
    check_dates(start_date, end_date)
    df = filter_df(STATE["obs"], start_date, end_date, sensor, platform, satellite, min_frp, max_frp)
    total = int(len(df))
    page = df.iloc[offset: offset + limit]
    return {"total": total, "limit": limit, "offset": offset, "count": int(len(page)),
            "observations": [obs_properties(r) for _, r in page.iterrows()]}


@app.get("/api/observations/{observation_id}")
def observation_detail(observation_id: str):
    obs = STATE["obs"]
    row = obs[obs["observation_id"] == observation_id] if not obs.empty else obs
    if row.empty:
        raise HTTPException(404, "Observation not found")
    return obs_properties(row.iloc[0])


@app.get("/api/hotspots/geojson")
def hotspots_geojson(start_date: Optional[str] = None, end_date: Optional[str] = None,
                     sensor: Optional[str] = None, platform: Optional[str] = None,
                     satellite: Optional[str] = None, min_frp: Optional[float] = None,
                     max_frp: Optional[float] = None,
                     limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)):
    check_dates(start_date, end_date)
    df = filter_df(STATE["obs"], start_date, end_date, sensor, platform, satellite, min_frp, max_frp)
    total = int(len(df))
    feats = []
    for _, r in df.iloc[:limit].iterrows():
        props = obs_properties(r)
        feats.append({"type": "Feature", "id": props["observation_id"],
                      "geometry": {"type": "Point", "coordinates": [float(r["longitude"]), float(r["latitude"])]},
                      "properties": props})
    return {"type": "FeatureCollection", "features": feats,
            "metadata": {"total_matching": total, "returned": len(feats), "truncated": total > len(feats),
                         "crs": "EPSG:4326", "coordinate_order": "[longitude, latitude]"}}


@app.get("/api/harmonization")
def harmonization(start_date: Optional[str] = None, end_date: Optional[str] = None,
                  sensor: Optional[str] = None, platform: Optional[str] = None,
                  grid_id: Optional[str] = None,
                  limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0)):
    check_dates(start_date, end_date)
    d = STATE["daily"]
    if not d.empty:
        d = d.assign(date=d["date"].astype(str))
    df = filter_df(d, start_date, end_date, sensor, platform)
    if grid_id and not df.empty:
        df = df[df["grid_id"] == grid_id]
    total = int(len(df))
    page = df.iloc[offset: offset + limit]
    recs = [{k: clean(v) for k, v in rec.items()} for rec in page.to_dict("records")]
    return {"total": total, "limit": limit, "offset": offset, "count": len(recs), "rows": recs,
            "note": "One row = one grid cell, one date, one platform. Platforms are not merged."}


@app.get("/api/statistics")
def statistics():
    if not STATE["stats"]:
        return {"by_sensor": [], "by_platform": [], "by_satellite": [], "daily_counts": [],
                "day_night": {"day": 0, "night": 0}, "notes": [DISCLAIMER]}
    return STATE["stats"]


@app.get("/api/grid/{grid_id}")
def grid_cell(grid_id: str):
    obs, sp = STATE["obs"], STATE["spatial"]
    sub = obs[obs["grid_id"] == grid_id] if not obs.empty else obs
    if sub.empty:
        raise HTTPException(404, "Grid cell not found")
    srow = sp[sp["grid_id"] == grid_id].iloc[0]
    plat = []
    for p, s in sub.groupby("platform"):
        frp = s["frp"].dropna()
        plat.append({"sensor": s["sensor"].iloc[0], "platform": p, "observation_count": int(len(s)),
                     "frp_mean": round(float(frp.mean()), 3) if len(frp) else None,
                     "frp_median": round(float(frp.median()), 3) if len(frp) else None,
                     "frp_max": round(float(frp.max()), 3) if len(frp) else None,
                     "dates": sorted(s["date"].unique().tolist())})
    d = STATE["daily"]
    daily = d[d["grid_id"] == grid_id] if not d.empty else d
    return {"grid_id": grid_id, "grid_x": int(srow["grid_x"]), "grid_y": int(srow["grid_y"]),
            "center": {"longitude": float(srow["center_longitude"]), "latitude": float(srow["center_latitude"])},
            "grid_size_km": 1.0, "observation_count": int(len(sub)),
            "platform_stats": plat,
            "daily": [{k: clean(v) for k, v in r.items()} for r in daily.to_dict("records")],
            "observations": [obs_properties(r) for _, r in sub.sort_values("acq_datetime").iterrows()],
            "note": "Detections sharing a cell/date are not necessarily the same fire."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=os.getenv("FIRESYNC_HOST", "0.0.0.0"), port=int(os.getenv("FIRESYNC_PORT", "8000")))
