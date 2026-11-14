"""FireSync harmonization: aggregates output/normalized_valid.csv.

Platforms are NEVER merged: every aggregate keeps sensor + platform (and satellite
where relevant). Confidence is kept as the original string, never converted.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
INPUT_CSV = OUTPUT_DIR / "normalized_valid.csv"
REJECTED_CSV = OUTPUT_DIR / "rejected_records.csv"
GRID_SIZE_M = 1000.0

_to_wgs84 = Transformer.from_crs("EPSG:6933", "EPSG:4326", always_xy=True)


def load_valid() -> pd.DataFrame:
    if not INPUT_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(INPUT_CSV, dtype={"acq_time": str, "confidence": str, "grid_id": str})
    if df.empty:
        return df
    df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["acq_datetime", "grid_id", "latitude", "longitude"]).copy()
    df["acq_time"] = df["acq_time"].str.zfill(4)
    df["date"] = df["acq_datetime"].dt.strftime("%Y-%m-%d")
    for c in ("frp", "brightness"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.reset_index(drop=True)


def add_observation_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic ID from source identity; source data is not modified."""
    df = df.copy()
    key = (df["source_file"].astype(str) + "|" + df["latitude"].astype(str) + "|"
           + df["longitude"].astype(str) + "|" + df["acq_date"].astype(str) + "|"
           + df["acq_time"].astype(str) + "|" + df["satellite"].astype(str))
    occ = key.groupby(key).cumcount().astype(str)  # disambiguates exact duplicates
    df["observation_id"] = [
        "obs_" + hashlib.sha1(f"{k}|{o}".encode()).hexdigest()[:12] for k, o in zip(key, occ)
    ]
    return df


def daily_harmonization(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["grid_id", "date", "sensor", "platform", "observation_count", "frp_mean",
            "frp_median", "frp_max", "brightness_mean", "day_count", "night_count",
            "first_observation", "last_observation"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    g = df.groupby(["grid_id", "date", "sensor", "platform"], sort=True)
    out = g.agg(
        observation_count=("observation_id", "size"),
        frp_mean=("frp", "mean"),
        frp_median=("frp", "median"),
        frp_max=("frp", "max"),
        brightness_mean=("brightness", "mean"),
        first_observation=("acq_datetime", "min"),
        last_observation=("acq_datetime", "max"),
    ).reset_index()
    dn = df.assign(_d=(df["daynight"] == "D").astype(int), _n=(df["daynight"] == "N").astype(int))
    dn = dn.groupby(["grid_id", "date", "sensor", "platform"], sort=True)[["_d", "_n"]].sum().reset_index()
    out = out.merge(dn, on=["grid_id", "date", "sensor", "platform"])
    out = out.rename(columns={"_d": "day_count", "_n": "night_count"})
    for c in ("frp_mean", "frp_median", "brightness_mean"):
        out[c] = out[c].round(3)
    for c in ("first_observation", "last_observation"):
        out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out[cols]


def _frp_summary(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"frp_mean": None, "frp_median": None, "frp_max": None}
    return {"frp_mean": round(float(s.mean()), 3), "frp_median": round(float(s.median()), 3),
            "frp_max": round(float(s.max()), 3)}


def _group_stats(df: pd.DataFrame, by: str) -> list:
    rows = []
    for key, sub in df.groupby(by, sort=True):
        row = {by: key, "observations": int(len(sub)), "unique_grid_cells": int(sub["grid_id"].nunique()),
               "day_count": int((sub["daynight"] == "D").sum()),
               "night_count": int((sub["daynight"] == "N").sum())}
        row.update(_frp_summary(sub["frp"]))
        row["daily_counts"] = {k: int(v) for k, v in sub.groupby("date").size().items()}
        rows.append(row)
    return rows


def platform_statistics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"by_sensor": [], "by_platform": [], "by_satellite": [], "daily_counts": [],
                "day_night": {"day": 0, "night": 0},
                "notes": NOTES}
    daily = (df.groupby(["date", "sensor", "platform", "satellite"]).size()
             .rename("observations").reset_index().to_dict("records"))
    return {
        "by_sensor": _group_stats(df, "sensor"),
        "by_platform": _group_stats(df, "platform"),
        "by_satellite": _group_stats(df, "satellite"),
        "daily_counts": daily,
        "day_night": {"day": int((df["daynight"] == "D").sum()), "night": int((df["daynight"] == "N").sum())},
        "notes": NOTES,
    }


NOTES = [
    "Observation counts reflect sensor overpasses, resolution and detection sensitivity; "
    "they do not indicate that one sensor is better than another.",
    "FRP values from different sensors are shown side by side and are never summed or merged.",
    "Confidence is the original NASA value (MODIS: 0-100 numeric; VIIRS: l/n/h categorical) and is not comparable across sensors.",
    "Unique grid cells are not unique fires; several detections in one cell/day may or may not be the same fire.",
    "Prototype built on NASA FIRMS NRT data; not validated or endorsed by NASA.",
]


def spatial_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["grid_id", "grid_x", "grid_y", "center_longitude", "center_latitude",
                                     "observation_count", "platform_counts", "frp_mean", "frp_median", "frp_max"])
    rows = []
    for gid, sub in df.groupby("grid_id", sort=True):
        gx, gy = int(sub["grid_x"].iloc[0]), int(sub["grid_y"].iloc[0])
        lon, lat = _to_wgs84.transform((gx + 0.5) * GRID_SIZE_M, (gy + 0.5) * GRID_SIZE_M)
        r = {"grid_id": gid, "grid_x": gx, "grid_y": gy,
             "center_longitude": round(lon, 6), "center_latitude": round(lat, 6),
             "observation_count": int(len(sub)),
             "platform_counts": json.dumps({k: int(v) for k, v in sub.groupby("platform").size().items()}),
             "first_date": sub["date"].min(), "last_date": sub["date"].max()}
        r.update(_frp_summary(sub["frp"]))
        rows.append(r)
    return pd.DataFrame(rows)


def integrity_report(df: pd.DataFrame, daily: pd.DataFrame) -> dict:
    rejected = len(pd.read_csv(REJECTED_CSV)) if REJECTED_CSV.exists() and REJECTED_CSV.stat().st_size > 5 else 0
    daily_total = int(daily["observation_count"].sum()) if len(daily) else 0
    return {"valid_records": int(len(df)), "rejected_records": int(rejected),
            "source_records": int(len(df) + rejected), "daily_aggregate_total": daily_total,
            "counts_match": daily_total == len(df), "unique_grid_cells": int(df["grid_id"].nunique()) if len(df) else 0,
            "unique_observation_ids": int(df["observation_id"].nunique()) if len(df) else 0}


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = load_valid()
    if not df.empty:
        df = add_observation_ids(df)
    daily = daily_harmonization(df)
    stats = platform_statistics(df)
    spatial = spatial_summary(df)
    report = integrity_report(df, daily)

    if not df.empty:
        df.sort_values(["acq_datetime", "observation_id"]).to_csv(OUTPUT_DIR / "observations_indexed.csv", index=False)
    else:
        pd.DataFrame().to_csv(OUTPUT_DIR / "observations_indexed.csv", index=False)
    daily.to_csv(OUTPUT_DIR / "harmonized_daily.csv", index=False)
    spatial.to_csv(OUTPUT_DIR / "spatial_summary.csv", index=False)
    (OUTPUT_DIR / "platform_statistics.json").write_text(json.dumps(stats, indent=2))
    (OUTPUT_DIR / "integrity_report.json").write_text(json.dumps(report, indent=2))

    print("Harmonization summary")
    print("---------------------")
    print(json.dumps(report, indent=2))
    print("Daily harmonized rows:", len(daily))
    print("Spatial summary rows:", len(spatial))
    assert report["counts_match"], "daily aggregates do not sum to valid observations"


if __name__ == "__main__":
    main()
