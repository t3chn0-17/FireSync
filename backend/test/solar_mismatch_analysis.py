
import pandas as pd
import numpy as np
from pvlib.solarposition import get_solarposition

INPUT_FILE = "output/match_details.csv"
OUTPUT_FILE = "output/solar_mismatch_analysis.csv"

df = pd.read_csv(INPUT_FILE)

def solar_elevation(timestamp, latitude, longitude):
    times = pd.DatetimeIndex(
        [pd.to_datetime(timestamp, utc=True)]
    )

    position = get_solarposition(
        times,
        latitude=float(latitude),
        longitude=float(longitude),
    )

    return float(position["apparent_elevation"].iloc[0])


modis_elevations = []
viirs_elevations = []

for _, row in df.iterrows():

    modis_elevations.append(
        solar_elevation(
            row["modis_datetime_utc"],
            row["modis_latitude"],
            row["modis_longitude"],
        )
    )

    viirs_elevations.append(
        solar_elevation(
            row["viirs_datetime_utc"],
            row["viirs_latitude"],
            row["viirs_longitude"],
        )
    )


df["modis_solar_elevation"] = modis_elevations
df["viirs_solar_elevation"] = viirs_elevations

df["solar_elevation_difference"] = (
    df["viirs_solar_elevation"]
    - df["modis_solar_elevation"]
)

df["daynight_agreement"] = (
    df["modis_daynight"] == df["viirs_daynight"]
)

# Exploratory diagnostic only, not NASA's official threshold.
HORIZON_MARGIN_DEGREES = 6

df["near_solar_terminator"] = (
    (df["modis_solar_elevation"].abs()
     <= HORIZON_MARGIN_DEGREES)
    |
    (df["viirs_solar_elevation"].abs()
     <= HORIZON_MARGIN_DEGREES)
)

print("\nSOLAR ELEVATION ANALYSIS")

print(
    df.groupby("platform").agg(
        matches=("platform", "size"),
        daynight_agreement=("daynight_agreement", "sum"),
        near_terminator=("near_solar_terminator", "sum"),
        mean_modis_elevation=(
            "modis_solar_elevation", "mean"
        ),
        mean_viirs_elevation=(
            "viirs_solar_elevation", "mean"
        ),
    ).round(3).to_string()
)

mismatches = df[~df["daynight_agreement"]].copy()

columns = [
    "platform",
    "modis_datetime_utc",
    "viirs_datetime_utc",
    "modis_daynight",
    "viirs_daynight",
    "modis_solar_elevation",
    "viirs_solar_elevation",
    "solar_elevation_difference",
    "near_solar_terminator",
    "distance_km",
    "time_difference_min",
]

print("\nDAY/NIGHT MISMATCHES WITH SOLAR ELEVATION")
print(
    mismatches[columns]
    .round(3)
    .to_string(index=False)
)

df.to_csv(OUTPUT_FILE, index=False)

print(f"\nSaved: {OUTPUT_FILE}")
