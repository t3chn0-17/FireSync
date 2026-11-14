
import pandas as pd

df = pd.read_csv("output/match_details.csv")

df["frp_symmetric_percent_difference"] = pd.to_numeric(
    df["frp_symmetric_percent_difference"],
    errors="coerce"
)

df["modis_frp"] = pd.to_numeric(
    df["modis_frp"], errors="coerce"
)

df["viirs_frp"] = pd.to_numeric(
    df["viirs_frp"], errors="coerce"
)

print("\nDAY/NIGHT AGREEMENT")
df["daynight_agreement"] = (
    df["modis_daynight"].astype(str).str.upper()
    ==
    df["viirs_daynight"].astype(str).str.upper()
)

print(
    df.groupby("platform")["daynight_agreement"]
    .agg(["count", "sum", "mean"])
    .to_string()
)

print("\nFRP DIFFERENCE BY DAY/NIGHT")

for platform, group in df.groupby("platform"):

    print(f"\n{platform}")

    for mode in ["D", "N"]:

        subset = group[
            (group["modis_daynight"] == mode)
            & (group["viirs_daynight"] == mode)
        ]

        if subset.empty:
            print(f"{mode}: no matched observations")
            continue

        print(
            f"{mode}: "
            f"n={len(subset)}, "
            f"median symmetric difference="
            f"{subset['frp_symmetric_percent_difference'].median():.2f}%, "
            f"median MODIS FRP="
            f"{subset['modis_frp'].median():.3f}, "
            f"median VIIRS FRP="
            f"{subset['viirs_frp'].median():.3f}"
        )

print("\nDAY/NIGHT MISMATCHED PAIRS")

mismatches = df[~df["daynight_agreement"]]

if mismatches.empty:
    print("No mismatched pairs.")
else:
    print(
        mismatches[
            [
                "platform",
                "modis_daynight",
                "viirs_daynight",
                "distance_km",
                "time_difference_min",
                "modis_frp",
                "viirs_frp",
            ]
        ].to_string(index=False)
    )
