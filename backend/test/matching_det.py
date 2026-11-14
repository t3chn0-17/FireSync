import pandas as pd

df = pd.read_csv("output/match_details.csv")

columns = [
    "platform",
    "distance_km",
    "time_difference_min",
    "modis_frp",
    "viirs_frp",
    "frp_symmetric_percent_difference",
]

print("\nMATCH DETAILS PREVIEW")
print(df[columns].head(10).to_string(index=False))

print("\nSUMMARY BY PLATFORM")
print(
    df.groupby("platform").agg(
        matches=("platform", "count"),
        avg_distance_km=("distance_km", "mean"),
        max_distance_km=("distance_km", "max"),
        avg_time_difference=("time_difference_min", "mean"),
        avg_frp_difference=("frp_symmetric_percent_difference", "mean"),
    ).round(3)
)