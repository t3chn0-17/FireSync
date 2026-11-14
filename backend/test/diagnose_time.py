
import pandas as pd
import numpy as np

from pathlib import Path
from pyproj import Transformer
from scipy.spatial.distance import cdist


BASE_DIR = Path(__file__).resolve().parent

df = pd.read_csv(
    BASE_DIR / "output" / "normalized_valid.csv",
    parse_dates=["acq_datetime"],
)

df["acq_datetime"] = pd.to_datetime(
    df["acq_datetime"], utc=True
)

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

df["x_m"] = x
df["y_m"] = y

modis = df[df["sensor"] == "MODIS"].reset_index(drop=True)

platforms = [
    "VIIRS_SNPP",
    "VIIRS_NOAA20",
    "VIIRS_NOAA21",
]

for platform in platforms:

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

    time_diff = np.abs(
        modis_times[:, None] - viirs_times[None, :]
    ) / 60

    print(f"\n{'=' * 45}")
    print(platform)

    for radius_km in [1, 2, 5, 10]:

        spatial_mask = distances <= radius_km * 1000
        differences = time_diff[spatial_mask]

        print(f"\nRadius: {radius_km} km")
        print("Spatial pairs:", len(differences))

        if len(differences) == 0:
            continue

        print("Minimum time difference:", differences.min())
        print("Median time difference:", np.median(differences))
        print("90th percentile:", np.percentile(differences, 90))
        print("Maximum time difference:", differences.max())

        for limit in [15, 30, 60, 90]:
            print(
                f"Within {limit} min:",
                np.sum(differences <= limit),
            )
