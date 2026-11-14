
import pandas as pd
import numpy as np

df = pd.read_csv("output/match_details.csv")

# Ensure numeric values
for col in [
    "modis_frp",
    "viirs_frp",
    "distance_km",
    "time_difference_min",
    "frp_symmetric_percent_difference",
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["signed_frp_difference"] = (
    df["viirs_frp"] - df["modis_frp"]
)

df["frp_ratio_viirs_to_modis"] = (
    df["viirs_frp"] / df["modis_frp"].replace(0, np.nan)
)

summary = df.groupby("platform").agg(
    match_count=("platform", "size"),

    mean_modis_frp=("modis_frp", "mean"),
    mean_viirs_frp=("viirs_frp", "mean"),

    median_modis_frp=("modis_frp", "median"),
    median_viirs_frp=("viirs_frp", "median"),

    mean_signed_difference=("signed_frp_difference", "mean"),
    median_signed_difference=("signed_frp_difference", "median"),

    mean_symmetric_difference=(
        "frp_symmetric_percent_difference", "mean"
    ),

    median_symmetric_difference=(
        "frp_symmetric_percent_difference", "median"
    ),

    median_frp_ratio=("frp_ratio_viirs_to_modis", "median"),

    mean_distance_km=("distance_km", "mean"),
    mean_time_difference_min=("time_difference_min", "mean"),
)

print("\nFRP ANALYSIS")
print(summary.round(3).to_string())

print("\nFRP DIRECTION")
for platform, group in df.groupby("platform"):
    viirs_higher = (
        group["signed_frp_difference"] > 0
    ).sum()

    modis_higher = (
        group["signed_frp_difference"] < 0
    ).sum()

    equal = (
        group["signed_frp_difference"] == 0
    ).sum()

    print(f"\n{platform}")
    print(f"VIIRS higher: {viirs_higher}")
    print(f"MODIS higher: {modis_higher}")
    print(f"Equal: {equal}")

print("\nCORRELATION (EXPLORATORY)")
for platform, group in df.groupby("platform"):
    valid = group[["modis_frp", "viirs_frp"]].dropna()

    if len(valid) >= 3:
        correlation = valid["modis_frp"].corr(
            valid["viirs_frp"]
        )
        print(f"{platform}: {correlation:.3f}")
    else:
        print(f"{platform}: insufficient observations")
