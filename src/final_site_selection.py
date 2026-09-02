import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR / "data/processed/location_accessibility.geojson"
)

OUTPUT_GEOJSON = (
    BASE_DIR / "data/processed/final_site_selection.geojson"
)

OUTPUT_CSV = (
    BASE_DIR / "data/processed/final_site_selection.csv"
)


# ============================================================
# SETTINGS
# ============================================================

print("=" * 25)
print("FINAL SITE SELECTION")
print("=" * 25)


# ============================================================
# LOAD DATA
# ============================================================

gdf = gpd.read_file(INPUT_FILE)

print(f"Rows: {len(gdf)}")
print(f"Columns: {len(gdf.columns)}")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def numeric_column(df, column):
    if column in df.columns:
        return pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)
    return pd.Series(0.0, index=df.index)


def min_max(series):

    series = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            0.5,
            index=series.index
        )

    return (series - minimum) / (maximum - minimum)


# ============================================================
# LOAD IMPORTANT FEATURES
# ============================================================

population = numeric_column(
    gdf,
    "Population"
)

income = numeric_column(
    gdf,
    "median_income"
)

poverty = numeric_column(
    gdf,
    "poverty_rate"
)

apartments = numeric_column(
    gdf,
    "apartment_count"
)

grocery_stores = numeric_column(
    gdf,
    "grocery_stores"
)

major_retailers = numeric_column(
    gdf,
    "major_retailers"
)

road_access = numeric_column(
    gdf,
    "road_access_score"
)

grocery_access = numeric_column(
    gdf,
    "grocery_access_score"
)

retail_access = numeric_column(
    gdf,
    "retail_access_score"
)


# ============================================================
# DEMAND SCORE
# ============================================================

print("\nCalculating demand score...")

population_score = min_max(population)

income_score = min_max(income)

apartment_score = min_max(apartments)

# Moderate poverty can indicate underserved markets,
# but extremely high poverty should not dominate the score.

poverty_score = 1 - min_max(poverty)


gdf["demand_score"] = (
    population_score * 0.40
    +
    income_score * 0.35
    +
    apartment_score * 0.25
)


# ============================================================
# COMPETITION SCORE
# ============================================================

print("Calculating competition score...")

grocery_competition = min_max(
    grocery_stores
)

retailer_competition = min_max(
    major_retailers
)

# Lower competition = better opportunity

gdf["competition_score"] = (
    (1 - grocery_competition) * 0.75
    +
    (1 - retailer_competition) * 0.25
)


# ============================================================
# ACCESSIBILITY SCORE
# ============================================================

print("Calculating accessibility score...")

gdf["accessibility_score_final"] = (
    grocery_access * 0.35
    +
    road_access * 0.45
    +
    retail_access * 0.20
)


# ============================================================
# UNDERSERVED MARKET SCORE
# ============================================================

print("Calculating underserved-market score...")

# High population + low grocery competition

population_normalized = min_max(
    population
)

competition_normalized = (
    1 - grocery_competition
)

gdf["underserved_score"] = (
    population_normalized * 0.60
    +
    competition_normalized * 0.40
)


# ============================================================
# FINAL SITE SELECTION SCORE
# ============================================================

print("Calculating final site-selection score...")

gdf["site_selection_score"] = (
    gdf["demand_score"] * 0.40
    +
    gdf["competition_score"] * 0.30
    +
    gdf["accessibility_score_final"] * 0.20
    +
    gdf["underserved_score"] * 0.10
)


# ============================================================
# LOCATION CATEGORY
# ============================================================

def category(score):

    if score >= 0.75:
        return "Excellent"

    elif score >= 0.65:
        return "High"

    elif score >= 0.55:
        return "Moderate"

    elif score >= 0.45:
        return "Low"

    else:
        return "Poor"


gdf["site_category"] = (
    gdf["site_selection_score"]
    .apply(category)
)


# ============================================================
# RANK
# ============================================================

gdf["site_rank"] = (
    gdf["site_selection_score"]
    .rank(
        ascending=False,
        method="min"
    )
    .astype(int)
)


# ============================================================
# SORT
# ============================================================

gdf = gdf.sort_values(
    "site_selection_score",
    ascending=False
).copy()


# ============================================================
# TOP 20
# ============================================================

print("\n" + "=" * 25)
print("TOP 20 SITE LOCATIONS")
print("=" * 25)

display_columns = [
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles",
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score",
    "site_selection_score",
    "site_category",
    "site_rank"
]

display_columns = [
    column
    for column in display_columns
    if column in gdf.columns
]

print(
    gdf[display_columns]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 25)
print("VALIDATION")
print("=" * 25)

print(
    "GEOID missing:",
    gdf["GEOID"].isna().sum()
)

print(
    "Score missing:",
    gdf["site_selection_score"].isna().sum()
)

print(
    "Score minimum:",
    round(gdf["site_selection_score"].min(), 4)
)

print(
    "Score maximum:",
    round(gdf["site_selection_score"].max(), 4)
)


# ============================================================
# SAVE GEOJSON
# ============================================================

gdf.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


# ============================================================
# SAVE CSV
# ============================================================

gdf.drop(
    columns="geometry"
).to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 25)
print("FINAL SITE SELECTION COMPLETE")
print("=" * 25)

print(f"Rows: {len(gdf)}")

print("\nSaved:")
print(OUTPUT_GEOJSON)
print(OUTPUT_CSV)

print("\nAnalysis complete!")
