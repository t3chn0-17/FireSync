
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree


INPUT_FILE = Path("output/normalized_valid.csv")

DISTANCES_KM = [1, 2, 5, 10]

TIME_LIMITS_MIN = [
    30,
    60,
    180,
    360,
    720,
    1440,
]

PLATFORMS = [
    "VIIRS_SNPP",
    "VIIRS_NOAA20",
    "VIIRS_NOAA21",
]

transformer = Transformer.from_crs(
    "EPSG:4326",
    "+proj=aeqd +lat_0=26 +lon_0=30 "
    "+datum=WGS84 +units=m +no_defs",
    always_xy=True,
)


def project(df):
    x, y = transformer.transform(
        df["longitude"].to_numpy(),
        df["latitude"].to_numpy(),
    )
    return np.column_stack((x, y))


def main():
    df = pd.read_csv(INPUT_FILE)

    df["acq_datetime"] = pd.to_datetime(
        df["acq_datetime"],
        utc=True,
        errors="raise",
    )

    modis = (
        df[df["platform"] == "MODIS"]
        .copy()
        .reset_index(drop=True)
    )

    modis_xy = project(modis)

    modis_times = modis["acq_datetime"].to_numpy(
        dtype="datetime64[ns]"
    )

    print("MODIS observations:", len(modis))
    print()

    for platform in PLATFORMS:

        viirs = (
            df[df["platform"] == platform]
            .copy()
            .reset_index(drop=True)
        )

        viirs_xy = project(viirs)

        viirs_times = viirs["acq_datetime"].to_numpy(
            dtype="datetime64[ns]"
        )

        tree = cKDTree(viirs_xy)

        print("=" * 65)
        print(platform)
        print("=" * 65)

        all_spatial_pairs = []

        for mi, nearby in enumerate(
            tree.query_ball_point(
                modis_xy,
                r=max(DISTANCES_KM) * 1000,
            )
        ):
            for vi in nearby:

                distance_km = (
                    np.linalg.norm(
                        modis_xy[mi] - viirs_xy[vi]
                    ) / 1000
                )

                time_diff_min = abs(
                    (
                        modis_times[mi]
                        - viirs_times[vi]
                    ) / np.timedelta64(1, "m")
                )

                all_spatial_pairs.append({
                    "modis_id": mi,
                    "viirs_id": vi,
                    "distance_km": distance_km,
                    "time_diff_min": float(time_diff_min),
                    "modis_time": modis.iloc[mi]["acq_datetime"],
                    "viirs_time": viirs.iloc[vi]["acq_datetime"],
                })

        pairs = pd.DataFrame(all_spatial_pairs)

        if pairs.empty:
            print("No spatial pairs within 10 km.")
            print()
            continue

        for distance in DISTANCES_KM:

            subset = pairs[
                pairs["distance_km"] <= distance
            ]

            print(
                f"\nSpatial radius: {distance} km"
            )
            print(
                f"Spatial pairs: {len(subset)}"
            )

            if subset.empty:
                continue

            print(
                "Minimum time difference:",
                round(subset["time_diff_min"].min(), 2),
                "minutes",
            )

            print(
                "Median time difference:",
                round(subset["time_diff_min"].median(), 2),
                "minutes",
            )

            for limit in TIME_LIMITS_MIN:
                count = (
                    subset["time_diff_min"] <= limit
                ).sum()

                print(
                    f"Within {limit:4} minutes: {count}"
                )

        print("\nClosest spatial pairs:")

        print(
            pairs.sort_values("distance_km")
            .head(5)[
                [
                    "distance_km",
                    "time_diff_min",
                    "modis_time",
                    "viirs_time",
                ]
            ]
            .to_string(index=False)
        )

        print()


if __name__ == "__main__":
    main()
