
import pandas as pd

df = pd.read_csv("output/match_details.csv")

date_columns = [
    "modis_datetime_utc",
    "viirs_datetime_utc",
]

for col in date_columns:
    df[col] = pd.to_datetime(df[col], utc=True)

df["actual_time_difference_min"] = (
    df["modis_datetime_utc"] - df["viirs_datetime_utc"]
).abs().dt.total_seconds() / 60

df["actual_date_difference_days"] = (
    df["modis_datetime_utc"].dt.date
    != df["viirs_datetime_utc"].dt.date
)

print("\nTIME VALIDATION")

print(
    df[
        [
            "platform",
            "modis_datetime_utc",
            "viirs_datetime_utc",
            "time_difference_min",
            "actual_time_difference_min",
            "actual_date_difference_days",
        ]
    ].to_string(index=False)
)

print("\nINVALID MATCHES")

invalid = df[
    df["actual_time_difference_min"] > 30
]

print(f"Invalid matches: {len(invalid)}")
print(invalid[
    [
        "platform",
        "modis_datetime_utc",
        "viirs_datetime_utc",
        "actual_time_difference_min",
    ]
].to_string(index=False))
