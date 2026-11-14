import pandas as pd

df = pd.read_csv("output/normalized_valid.csv")

times = pd.to_datetime(df["acq_datetime"], utc=True)

print("Pandas version:", pd.__version__)
print("Datetime dtype:", times.dtype)
print("Integer representation:", times.astype("int64").head().tolist())

print("\nDirect timedelta calculation:")
print(
    (times.iloc[0] - times.iloc[1]).total_seconds() / 60
)