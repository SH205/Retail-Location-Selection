import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path("/Users/sh/Downloads/R")

TRACTS_FILE = BASE_DIR / "data/processed/final_market_features.geojson"

GROCERY_FILE = BASE_DIR / "data/processed/food_retail_clean.geojson"

RETAILER_FILE = (
    BASE_DIR / "data/raw/Data_geojson/Orlando_Major_Retailers.geojson"
)

ROADS_FILE = (
    BASE_DIR / "data/raw/Data_geojson/Orlando_Primary_Roads.geojson"
)

OUTPUT_GEOJSON = (
    BASE_DIR / "data/processed/location_accessibility.geojson"
)

OUTPUT_CSV = (
    BASE_DIR / "data/processed/location_accessibility.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# Distance calculations use meters.
PROJECTED_CRS = "EPSG:26917"  # NAD83 / UTM zone 17N


# ============================================================
# HELPER FUNCTION
# ============================================================

def nearest_distance(points, targets):
    """
    Calculate distance from each point to the nearest target.
    Returns distance in meters.
    """

    if len(targets) == 0:
        return np.nan

    distances = points.geometry.apply(
        lambda point: targets.distance(point).min()
    )

    return distances


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 25)
print("ACCESSIBILITY ANALYSIS")
print("=" * 25)

print("\nLoading census tracts...")
tracts = gpd.read_file(TRACTS_FILE)

print(f"Tracts: {len(tracts)}")

print("\nLoading grocery stores...")
grocery = gpd.read_file(GROCERY_FILE)

print(f"Grocery stores: {len(grocery)}")

print("\nLoading major retailers...")
retailers = gpd.read_file(RETAILER_FILE)

print(f"Major retailers: {len(retailers)}")

print("\nLoading roads...")
roads = gpd.read_file(ROADS_FILE)

print(f"Road segments: {len(roads)}")


# ============================================================
# VALIDATE GEOMETRY
# ============================================================

print("\nValidating geometries...")

tracts = tracts[tracts.geometry.notna()].copy()
grocery = grocery[grocery.geometry.notna()].copy()
retailers = retailers[retailers.geometry.notna()].copy()
roads = roads[roads.geometry.notna()].copy()


# ============================================================
# PROJECT TO METRIC CRS
# ============================================================

print("Projecting data to UTM...")

tracts = tracts.to_crs(PROJECTED_CRS)
grocery = grocery.to_crs(PROJECTED_CRS)
retailers = retailers.to_crs(PROJECTED_CRS)
roads = roads.to_crs(PROJECTED_CRS)


# ============================================================
# CREATE TRACT CENTROIDS
# ============================================================

print("Creating census tract centroids...")

tract_points = tracts.copy()

tract_points["geometry"] = tract_points.geometry.centroid


# ============================================================
# NEAREST GROCERY STORE
# ============================================================

print("Calculating nearest grocery-store distance...")

tract_points["nearest_grocery_m"] = nearest_distance(
    tract_points,
    grocery
)

tract_points["nearest_grocery_miles"] = (
    tract_points["nearest_grocery_m"] / 1609.344
)


# ============================================================
# NEAREST MAJOR RETAILER
# ============================================================

print("Calculating nearest major-retailer distance...")

tract_points["nearest_retailer_m"] = nearest_distance(
    tract_points,
    retailers
)

tract_points["nearest_retailer_miles"] = (
    tract_points["nearest_retailer_m"] / 1609.344
)


# ============================================================
# NEAREST MAJOR ROAD
# ============================================================

print("Calculating nearest major-road distance...")

# Use road geometry directly.
# Distance from tract centroid to nearest road segment.

tract_points["nearest_road_m"] = nearest_distance(
    tract_points,
    roads
)

tract_points["nearest_road_miles"] = (
    tract_points["nearest_road_m"] / 1609.344
)


# ============================================================
# GROCERY DENSITY
# ============================================================

print("Calculating grocery density...")

if "Population" in tract_points.columns:

    population = pd.to_numeric(
        tract_points["Population"],
        errors="coerce"
    ).fillna(0)

    grocery_count = pd.to_numeric(
        tract_points["grocery_stores"],
        errors="coerce"
    ).fillna(0)

    tract_points["grocery_stores_per_10000"] = np.where(
        population > 0,
        grocery_count / population * 10000,
        0
    )

else:

    tract_points["grocery_stores_per_10000"] = 0


# ============================================================
# ACCESSIBILITY SCORES
# ============================================================

print("Creating accessibility scores...")


# ------------------------------------------------------------
# Grocery accessibility
# ------------------------------------------------------------

# Lower distance = better opportunity.
# Convert distance into a 0-1 score.

grocery_distance = tract_points["nearest_grocery_miles"]

tract_points["grocery_access_score"] = (
    1 / (1 + grocery_distance)
)

tract_points["grocery_access_score"] = (
    tract_points["grocery_access_score"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)


# ------------------------------------------------------------
# Road accessibility
# ------------------------------------------------------------

road_distance = tract_points["nearest_road_miles"]

tract_points["road_access_score"] = (
    1 / (1 + road_distance)
)

tract_points["road_access_score"] = (
    tract_points["road_access_score"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)


# ------------------------------------------------------------
# Retail accessibility
# ------------------------------------------------------------

retail_distance = tract_points["nearest_retailer_miles"]

tract_points["retail_access_score"] = (
    1 / (1 + retail_distance)
)

tract_points["retail_access_score"] = (
    tract_points["retail_access_score"]
    .replace([np.inf, -np.inf], np.nan)
    .fillna(0)
)


# ============================================================
# NORMALIZE SCORES
# ============================================================

def min_max(series):

    series = series.astype(float)

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            0.5,
            index=series.index
        )

    return (series - minimum) / (maximum - minimum)


tract_points["grocery_access_score"] = min_max(
    tract_points["grocery_access_score"]
)

tract_points["road_access_score"] = min_max(
    tract_points["road_access_score"]
)

tract_points["retail_access_score"] = min_max(
    tract_points["retail_access_score"]
)


# ============================================================
# FINAL ACCESSIBILITY SCORE
# ============================================================

tract_points["accessibility_score"] = (
    tract_points["grocery_access_score"] * 0.40
    +
    tract_points["road_access_score"] * 0.40
    +
    tract_points["retail_access_score"] * 0.20
)


# ============================================================
# COMBINE WITH EXISTING OPPORTUNITY SCORE
# ============================================================

print("Creating final location score...")

if "opportunity_score" in tract_points.columns:

    existing_score = pd.to_numeric(
        tract_points["opportunity_score"],
        errors="coerce"
    ).fillna(0)

    tract_points["final_location_score"] = (
        existing_score * 0.70
        +
        tract_points["accessibility_score"] * 0.30
    )

else:

    tract_points["final_location_score"] = (
        tract_points["accessibility_score"]
    )


# ============================================================
# RANK LOCATIONS
# ============================================================

tract_points["location_rank"] = (
    tract_points["final_location_score"]
    .rank(
        ascending=False,
        method="min"
    )
    .astype(int)
)


# ============================================================
# SORT
# ============================================================

tract_points = tract_points.sort_values(
    "final_location_score",
    ascending=False
).copy()


# ============================================================
# DISPLAY TOP 20
# ============================================================

print("\n" + "=" * 25)
print("TOP 20 LOCATIONS")
print("=" * 25)

display_columns = [
    "GEOID",
    "Population",
    "median_income",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_retailer_miles",
    "nearest_road_miles",
    "opportunity_score",
    "accessibility_score",
    "final_location_score",
    "location_rank"
]

display_columns = [
    col for col in display_columns
    if col in tract_points.columns
]

print(
    tract_points[display_columns]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# CONVERT BACK TO WGS84
# ============================================================

print("\nConverting back to WGS84...")

output = tract_points.to_crs("EPSG:4326")


# ============================================================
# SAVE GEOJSON
# ============================================================

output.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


# ============================================================
# SAVE CSV
# ============================================================

csv_output = output.drop(
    columns="geometry"
)

csv_output.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 25)
print("ACCESSIBILITY ANALYSIS COMPLETE")
print("=" * 25)

print(f"Rows: {len(output)}")

print(
    "GEOID missing:",
    output["GEOID"].isna().sum()
)

print(
    "Final score missing:",
    output["final_location_score"].isna().sum()
)

print("\nSaved:")
print(OUTPUT_GEOJSON)
print(OUTPUT_CSV)

print("\nAnalysis complete!")