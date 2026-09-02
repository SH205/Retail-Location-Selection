import pandas as pd
import geopandas as gpd
from pathlib import Path

# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data/processed/final_market_features.geojson"
OUTPUT_DIR = BASE_DIR / "data/processed"

OUTPUT_CSV = OUTPUT_DIR / "market_analysis_results.csv"

# =========================
# LOAD DATA
# =========================

print("=========================")
print("MARKET ANALYSIS")
print("=========================")

gdf = gpd.read_file(INPUT_FILE)

print(f"Rows: {len(gdf)}")
print(f"Columns: {len(gdf.columns)}")

# =========================
# BASIC VALIDATION
# =========================

required_columns = [
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "major_road_segments",
    "opportunity_score",
    "location_rank"
]

missing = [
    col for col in required_columns
    if col not in gdf.columns
]

if missing:
    raise ValueError(f"Missing columns: {missing}")

print("\nValidation:")
print(f"GEOID missing: {gdf['GEOID'].isna().sum()}")

# =========================
# CREATE ANALYSIS DATAFRAME
# =========================

df = pd.DataFrame(gdf.drop(columns="geometry"))

# Convert numeric columns safely
numeric_columns = [
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "major_road_segments",
    "opportunity_score",
    "location_rank"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# COMPETITION METRICS
# =========================

df["grocery_stores_per_10000"] = (
    df["grocery_stores"] /
    df["Population"].replace(0, pd.NA)
) * 10000

df["population_per_grocery_store"] = (
    df["Population"] /
    df["grocery_stores"].replace(0, pd.NA)
)

df["retail_competition"] = (
    df["grocery_stores"] +
    df["major_retailers"]
)

# =========================
# MARKET DEMAND METRICS
# =========================

df["population_density_proxy"] = (
    df["Population"] /
    df["apartment_count"].replace(0, pd.NA)
)

# =========================
# OPPORTUNITY CATEGORIES
# =========================

def classify_opportunity(score):

    if pd.isna(score):
        return "Unknown"

    if score >= 0.75:
        return "Excellent"

    elif score >= 0.70:
        return "High"

    elif score >= 0.65:
        return "Moderate"

    else:
        return "Low"


df["opportunity_category"] = (
    df["opportunity_score"]
    .apply(classify_opportunity)
)

# =========================
# TOP LOCATIONS
# =========================

top_locations = (
    df.sort_values(
        "opportunity_score",
        ascending=False
    )
    .head(20)
)

print("\n=========================")
print("TOP 20 LOCATIONS")
print("=========================")

print(
    top_locations[
        [
            "GEOID",
            "Population",
            "median_income",
            "poverty_rate",
            "grocery_stores",
            "apartment_count",
            "major_retailers",
            "major_road_segments",
            "opportunity_score",
            "opportunity_category"
        ]
    ].to_string(index=False)
)

# =========================
# BEST LOW-COMPETITION MARKETS
# =========================

low_competition = (
    df[
        (df["Population"] >= 5000) &
        (df["grocery_stores"] <= 5)
    ]
    .sort_values(
        "opportunity_score",
        ascending=False
    )
    .head(20)
)

print("\n=========================")
print("BEST LOW-COMPETITION MARKETS")
print("=========================")

print(
    low_competition[
        [
            "GEOID",
            "Population",
            "median_income",
            "poverty_rate",
            "grocery_stores",
            "apartment_count",
            "major_road_segments",
            "opportunity_score"
        ]
    ].to_string(index=False)
)

# =========================
# SAVE RESULTS
# =========================

df.to_csv(
    OUTPUT_CSV,
    index=False
)

print("\n=========================")
print("ANALYSIS COMPLETE")
print("=========================")

print(f"Saved: {OUTPUT_CSV}")
