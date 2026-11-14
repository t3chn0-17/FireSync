
import numpy as np
import pandas as pd

from pathlib import Path
from pyproj import Transformer
from scipy.spatial.distance import cdist


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "output" / "normalized_valid.csv"
OUTPUT_DIR = BASE_DIR / "output"

DISTANCES_KM = [1, 2, 5, 10]
TIMES_MINUTES = [30, 60, 90]

PLATFORMS = [
    "VIIRS_SNPP",
    "VIIRS_NOAA20",
    "VIIRS_NOAA21",
]


def project_coordinates(df):
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "+proj=aeqd +lat_0=26 +lon_0=30 "
        "+datum=WGS84 +units=m +no_defs",
        always_xy=True,
    )

    x, y = transformer.transform(
        df["longitude"].to_numpy(),
        df["latitude"].to_numpy(),
    )

    result = df.copy()
    result["x_m"] = x
    result["y_m"] = y

    return result


def greedy_one_to_one(candidates):
    """
    Experimental greedy one-to-one matching.
    """
    candidates = sorted(
        candidates,
        key=lambda pair: (pair[0], pair[1])
    )

    used_modis = set()
    used_viirs = set()

    for distance, time_diff, m_idx, v_idx in candidates:
        if m_idx in used_modis or v_idx in used_viirs:
            continue

        used_modis.add(m_idx)
        used_viirs.add(v_idx)

    return len(used_modis)


def main():
    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["acq_datetime"],
    )

    df["acq_datetime"] = pd.to_datetime(
        df["acq_datetime"],
        utc=True,
    )

    df = project_coordinates(df)

    modis = df[df["sensor"] == "MODIS"].reset_index(drop=True)

    results = []

    for platform in PLATFORMS:
        viirs = (
            df[df["platform"] == platform]
            .reset_index(drop=True)
        )

        distances = cdist(
            modis[["x_m", "y_m"]].to_numpy(),
            viirs[["x_m", "y_m"]].to_numpy(),
        )

        modis_times = (
            modis["acq_datetime"].astype("int64").to_numpy()
            / 1e9
        )

        viirs_times = (
            viirs["acq_datetime"].astype("int64").to_numpy()
            / 1e9
        )

        time_differences = np.abs(
            modis_times[:, None] - viirs_times[None, :]
        ) / 60

        print(f"\n{platform}")

        for distance_km in DISTANCES_KM:
            for time_minutes in TIMES_MINUTES:

                mask = (
                    (distances <= distance_km * 1000)
                    & (time_differences <= time_minutes)
                )

                modis_indices, viirs_indices = np.where(mask)

                candidates = [
                    (
                        distances[m, v],
                        time_differences[m, v],
                        m,
                        v,
                    )
                    for m, v in zip(
                        modis_indices,
                        viirs_indices,
                    )
                ]

                unique_matches = greedy_one_to_one(
                    candidates
                )

                results.append({
                    "platform": platform,
                    "max_distance_km": distance_km,
                    "max_time_minutes": time_minutes,
                    "candidate_pairs": len(candidates),
                    "one_to_one_matches": unique_matches,
                })

                print(
                    f"{distance_km:>2} km / "
                    f"{time_minutes:>2} min | "
                    f"candidate pairs: {len(candidates):>3} | "
                    f"one-to-one: {unique_matches:>2}"
                )

    report = pd.DataFrame(results)

    report.to_csv(
        OUTPUT_DIR / "sensitivity_results.csv",
        index=False,
    )

    print("\nSaved sensitivity_results.csv")


if __name__ == "__main__":
    main()
