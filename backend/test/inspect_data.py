import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")

files = {
    "MODIS": "fire_nrt_M-C61_844737.csv",
    "VIIRS_SNPP": "fire_nrt_SV-C2_844740.csv",
    "VIIRS_NOAA20": "fire_nrt_J1V-C2_844738.csv",
    "VIIRS_NOAA21": "fire_nrt_J2V-C2_844739.csv",
}

for sensor, filename in files.items():
    path = DATA_DIR / filename
    df = pd.read_csv(path)

    print(f"\n{'=' * 55}")
    print(f"SENSOR: {sensor}")
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())
    print("\nData types:")
    print(df.dtypes)
    print("\nSample:")
    print(df.head(3).to_string(index=False))
    print("\nMissing values:")
    print(df.isna().sum())
