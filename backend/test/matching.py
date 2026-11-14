from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree


# ============================================================
# Configuration
# ============================================================

INPUT_FILE = Path("output/normalized_valid.csv")
OUTPUT_DIR = Path("output")

DISTANCE_THRESHOLD_KM = 1.0
TIME_THRESHOLD_MIN = 30.0

VIIRS_PLATFORMS = [
    "VIIRS_SNPP",
    "VIIRS_NOAA20",
    "VIIRS_NOAA21",
]

# Local metric projection suitable for Egypt.
transformer = Transformer.from_crs(
    "EPSG:4326",
    "+proj=aeqd +lat_0=26 +lon_0=30 "
    "+datum=WGS84 +units=m +no_defs",
    always_xy=True,
)


# ============================================================
# Helpers
# ============================================================

def project_coordinates(df):
    x, y = transformer.transform(
        df["longitude"].to_numpy(dtype=float),
        df["latitude"].to_numpy(dtype=float),
    )

    return np.column_stack((x, y))


def safe_float(value):
    if pd.isna(value):
        return np.nan
    return float(value)


def symmetric_percent_difference(a, b):
    if pd.isna(a) or pd.isna(b):
        return np.nan

    denominator = (abs(a) + abs(b)) / 2

    if denominator == 0:
        return np.nan

    return abs(a - b) / denominator * 100


def prepare_datetime(series):
    """
    Parse timestamps as UTC and convert them to a consistent
    NumPy datetime64[ns] representation.

    Explicit conversion avoids assumptions about Pandas'
    internal datetime storage unit.
    """
    parsed = pd.to_datetime(
        series,
        utc=True,
        errors="coerce",
    )

    return parsed.to_numpy(dtype="datetime64[ns]")


def validate_input(df):
    required_columns = {
        "platform",
        "latitude",
        "longitude",
        "acq_datetime",
        "frp",
        "brightness",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df = df.copy()

    df["latitude"] = pd.to_numeric(
        df["latitude"], errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"], errors="coerce"
    )

    timestamps = pd.to_datetime(
        df["acq_datetime"],
        utc=True,
        errors="coerce",
    )

    invalid = (
        df["latitude"].isna()
        | df["longitude"].isna()
        | timestamps.isna()
        | ~df["latitude"].between(-90, 90)
        | ~df["longitude"].between(-180, 180)
    )

    if invalid.any():
        raise ValueError(
            f"Found {invalid.sum()} records with invalid "
            "coordinates or timestamps. Fix the input data first."
        )

    df["acq_datetime"] = timestamps

    return df


# ============================================================
# Matching
# ============================================================

def match_platform(modis, viirs, platform):

    modis = modis.copy().reset_index(drop=True)
    viirs = viirs.copy().reset_index(drop=True)

    if modis.empty or viirs.empty:
        return [], set(), set(), 0

    # Spatial coordinates in meters.
    modis_xy = project_coordinates(modis)
    viirs_xy = project_coordinates(viirs)

    tree = cKDTree(viirs_xy)

    nearby_indices = tree.query_ball_point(
        modis_xy,
        r=DISTANCE_THRESHOLD_KM * 1000,
    )

    # Explicitly normalize timestamps to nanoseconds.
    modis_times = prepare_datetime(
        modis["acq_datetime"]
    )

    viirs_times = prepare_datetime(
        viirs["acq_datetime"]
    )

    candidates = []

    for mi, nearby in enumerate(nearby_indices):

        for vi in nearby:

            distance_m = float(
                np.linalg.norm(
                    modis_xy[mi] - viirs_xy[vi]
                )
            )

            # Calculate actual elapsed time using timedeltas.
            time_delta = abs(
                modis_times[mi] - viirs_times[vi]
            )

            time_diff_min = float(
                time_delta / np.timedelta64(1, "m")
            )

            # Defensive validation.
            if distance_m > DISTANCE_THRESHOLD_KM * 1000:
                continue

            if time_diff_min > TIME_THRESHOLD_MIN:
                continue

            candidates.append(
                (distance_m, time_diff_min, mi, vi)
            )

    # Greedy assignment:
    # shortest distance first, then smallest time difference.
    candidates.sort(key=lambda x: (x[0], x[1]))

    used_modis = set()
    used_viirs = set()

    matched_records = []

    for distance_m, time_diff_min, mi, vi in candidates:

        if mi in used_modis or vi in used_viirs:
            continue

        used_modis.add(mi)
        used_viirs.add(vi)

        m = modis.iloc[mi]
        v = viirs.iloc[vi]

        modis_frp = safe_float(m["frp"])
        viirs_frp = safe_float(v["frp"])

        modis_brightness = safe_float(m["brightness"])
        viirs_brightness = safe_float(v["brightness"])

        frp_difference = (
            viirs_frp - modis_frp
            if not (
                pd.isna(modis_frp)
                or pd.isna(viirs_frp)
            )
            else np.nan
        )

        brightness_difference = (
            viirs_brightness - modis_brightness
            if not (
                pd.isna(modis_brightness)
                or pd.isna(viirs_brightness)
            )
            else np.nan
        )

        matched_records.append({

            "platform": platform,

            "modis_record_id": m.get(
                "record_id", mi
            ),

            "viirs_record_id": v.get(
                "record_id", vi
            ),

            "modis_source_file": m.get("source_file"),
            "viirs_source_file": v.get("source_file"),

            "modis_datetime_utc": m["acq_datetime"],
            "viirs_datetime_utc": v["acq_datetime"],

            "time_difference_min": time_diff_min,
            "distance_km": distance_m / 1000,

            "modis_latitude": m["latitude"],
            "modis_longitude": m["longitude"],

            "viirs_latitude": v["latitude"],
            "viirs_longitude": v["longitude"],

            "modis_frp": modis_frp,
            "viirs_frp": viirs_frp,

            "frp_difference_viirs_minus_modis":
                frp_difference,

            "frp_absolute_difference": (
                abs(frp_difference)
                if not pd.isna(frp_difference)
                else np.nan
            ),

            "frp_symmetric_percent_difference":
                symmetric_percent_difference(
                    modis_frp,
                    viirs_frp,
                ),

            "modis_brightness": modis_brightness,
            "viirs_brightness": viirs_brightness,

            "brightness_difference_viirs_minus_modis":
                brightness_difference,

            "modis_confidence": m.get("confidence"),
            "viirs_confidence": v.get("confidence"),

            "modis_daynight": m.get("daynight"),
            "viirs_daynight": v.get("daynight"),

            "distance_threshold_km":
                DISTANCE_THRESHOLD_KM,

            "time_threshold_min":
                TIME_THRESHOLD_MIN,

            "matching_method":
                "greedy_nearest_distance",

        })

    return (
        matched_records,
        used_modis,
        used_viirs,
        len(candidates),
    )


# ============================================================
# Main
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_csv(INPUT_FILE)

    df = validate_input(df)

    # Preserve original input row IDs.
    df = df.reset_index(drop=True)
    df["record_id"] = df.index

    modis = (
        df[df["platform"] == "MODIS"]
        .copy()
        .reset_index(drop=True)
    )

    all_matches = []
    all_unmatched = []
    summaries = []

    print(f"MODIS observations: {len(modis)}")
    print()

    for platform in VIIRS_PLATFORMS:

        viirs = (
            df[df["platform"] == platform]
            .copy()
            .reset_index(drop=True)
        )

        print(f"Comparing MODIS with {platform}")

        (
            matches,
            used_modis,
            used_viirs,
            candidate_count,
        ) = match_platform(
            modis,
            viirs,
            platform,
        )

        all_matches.extend(matches)

        unmatched_modis = (
            len(modis) - len(used_modis)
        )

        unmatched_viirs = (
            len(viirs) - len(used_viirs)
        )

        summaries.append({

            "platform": platform,

            "modis_observations": len(modis),

            "viirs_observations": len(viirs),

            "candidate_pairs": candidate_count,

            "matched_pairs": len(matches),

            "unmatched_modis": unmatched_modis,

            "unmatched_viirs": unmatched_viirs,

        })

        for i in range(len(modis)):

            if i not in used_modis:

                record = modis.iloc[i]

                all_unmatched.append({

                    "platform": platform,
                    "sensor": "MODIS",

                    "record_id": record["record_id"],

                    "latitude": record["latitude"],
                    "longitude": record["longitude"],

                    "acq_datetime": record["acq_datetime"],

                    "frp": record["frp"],

                })

        for i in range(len(viirs)):

            if i not in used_viirs:

                record = viirs.iloc[i]

                all_unmatched.append({

                    "platform": platform,
                    "sensor": platform,

                    "record_id": record["record_id"],

                    "latitude": record["latitude"],
                    "longitude": record["longitude"],

                    "acq_datetime": record["acq_datetime"],

                    "frp": record["frp"],

                })

        print(f"Candidate pairs: {candidate_count}")
        print(f"Matched pairs: {len(matches)}")
        print(f"MODIS unmatched: {unmatched_modis}")
        print(f"VIIRS unmatched: {unmatched_viirs}")
        print()

    matches_df = pd.DataFrame(all_matches)
    unmatched_df = pd.DataFrame(all_unmatched)
    summary_df = pd.DataFrame(summaries)

    # Final safety check on generated matches.
    if not matches_df.empty:

        check = (
            pd.to_datetime(
                matches_df["modis_datetime_utc"],
                utc=True,
            )
            -
            pd.to_datetime(
                matches_df["viirs_datetime_utc"],
                utc=True,
            )
        ).abs().dt.total_seconds() / 60

        if (check > TIME_THRESHOLD_MIN).any():
            raise RuntimeError(
                "Invalid temporal matches detected. "
                "Output files were not written."
            )

        matches_df["verified_time_difference_min"] = check

    matches_df.to_csv(
        OUTPUT_DIR / "match_details.csv",
        index=False,
    )

    unmatched_df.to_csv(
        OUTPUT_DIR / "unmatched_records.csv",
        index=False,
    )

    summary_df.to_csv(
        OUTPUT_DIR / "matching_summary.csv",
        index=False,
    )

    print("Files saved:")
    print(" - output/match_details.csv")
    print(" - output/unmatched_records.csv")
    print(" - output/matching_summary.csv")


if __name__ == "__main__":
    main()
