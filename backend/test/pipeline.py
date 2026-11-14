
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

FILES = {
    "MODIS": "fire_nrt_M-C61_844737.csv",
    "VIIRS_SNPP": "fire_nrt_SV-C2_844740.csv",
    "VIIRS_NOAA20": "fire_nrt_J1V-C2_844738.csv",
    "VIIRS_NOAA21": "fire_nrt_J2V-C2_844739.csv",
}

GRID_SIZE_KM = 1.0


def load_data():
    frames = []

    for platform, filename in FILES.items():
        path = DATA_DIR / filename
        df = pd.read_csv(path)

        df["sensor"] = (
            "MODIS" if platform == "MODIS" else "VIIRS"
        )
        df["platform"] = platform
        df["source_file"] = filename

        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def normalize_schema(df):
    df = df.copy()

    # Normalize numeric fields
    numeric_columns = [
        "latitude",
        "longitude",
        "brightness",
        "bright_t31",
        "frp",
        "scan",
        "track",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # Preserve original confidence values.
    # MODIS numeric confidence and VIIRS categorical
    # confidence are not directly equivalent.
    df["confidence"] = df["confidence"].astype("string")

    # Convert acquisition time HHMM into a UTC timestamp.
    time_digits = (
        pd.to_numeric(df["acq_time"], errors="coerce")
        .astype("Int64")
        .astype("string")
        .str.zfill(4)
    )

    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + time_digits,
        format="%Y-%m-%d %H%M",
        errors="coerce",
        utc=True,
    )

    return df


def validate_data(df):
    df = df.copy()

    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(mask, message):
        nonlocal reasons
        reasons.loc[mask] = (
            reasons.loc[mask] + message + "; "
        )

    add_reason(
        df["latitude"].isna()
        | ~df["latitude"].between(-90, 90),
        "invalid_latitude",
    )

    add_reason(
        df["longitude"].isna()
        | ~df["longitude"].between(-180, 180),
        "invalid_longitude",
    )

    add_reason(
        df["acq_datetime"].isna(),
        "invalid_datetime",
    )

    add_reason(
        df["frp"].isna() | (df["frp"] < 0),
        "invalid_frp",
    )

    add_reason(
        df["brightness"].isna(),
        "invalid_brightness",
    )

    df["validation_reason"] = reasons.str.rstrip("; ")
    df["is_valid"] = df["validation_reason"].eq("")

    valid = df[df["is_valid"]].copy()
    rejected = df[~df["is_valid"]].copy()

    return valid, rejected


def assign_spatial_grid(df, grid_size_km=1.0):
    df = df.copy()

    # EPSG:6933 is a global equal-area projected CRS.
    # Coordinates are transformed into meters.
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6933",
        always_xy=True,
    )

    x, y = transformer.transform(
        df["longitude"].to_numpy(),
        df["latitude"].to_numpy(),
    )

    cell_size_m = grid_size_km * 1000

    df["grid_x"] = np.floor(x / cell_size_m).astype("int64")
    df["grid_y"] = np.floor(y / cell_size_m).astype("int64")

    df["grid_id"] = (
        df["grid_x"].astype(str)
        + "_"
        + df["grid_y"].astype(str)
    )

    return df


def main():
    print("Loading data...")
    df = load_data()

    print("Normalizing schema...")
    df = normalize_schema(df)

    print("Validating observations...")
    valid, rejected = validate_data(df)

    print("Assigning spatial grid...")
    valid = assign_spatial_grid(
        valid,
        grid_size_km=GRID_SIZE_KM,
    )

    # Keep rejected records for quality-control review.
    valid.to_csv(
        OUTPUT_DIR / "normalized_valid.csv",
        index=False,
    )

    rejected.to_csv(
        OUTPUT_DIR / "rejected_records.csv",
        index=False,
    )

    print("\nPipeline summary")
    print("----------------------------")
    print("Total records:", len(df))
    print("Valid records:", len(valid))
    print("Rejected records:", len(rejected))

    print("\nRecords by platform:")
    print(valid.groupby("platform").size())

    print("\nRecords by day:")
    print(
        valid.groupby(
            valid["acq_datetime"].dt.date
        ).size()
    )

    print("\nUnique spatial cells:", valid["grid_id"].nunique())

    print("\nOutput saved in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
