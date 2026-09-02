import geopandas as gpd
from pathlib import Path


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"

PROCESSED.mkdir(parents=True, exist_ok=True)


# =========================
# LOAD ORIGINAL DATA
# =========================

input_file = (
    RAW / "Data_geojson" / "Orlando_Food_Retail.geojson"
)

food_retail = gpd.read_file(input_file)

print("Original grocery features:", len(food_retail))


# =========================
# REMOVE EXACT DUPLICATES
# =========================

food_retail_clean = food_retail.drop_duplicates().copy()

print(
    "After exact duplicates:",
    len(food_retail_clean)
)


# =========================
# REMOVE INVALID GEOMETRIES
# =========================

food_retail_clean = food_retail_clean[
    food_retail_clean.geometry.notna()
].copy()

food_retail_clean = food_retail_clean[
    food_retail_clean.geometry.is_valid
].copy()


# =========================
# REMOVE DUPLICATE GEOMETRIES
# =========================

food_retail_clean["geometry_wkt"] = (
    food_retail_clean.geometry.to_wkt()
)

food_retail_clean = (
    food_retail_clean
    .drop_duplicates(subset=["geometry_wkt"])
    .drop(columns=["geometry_wkt"])
)


# =========================
# SAVE CLEAN DATA
# =========================

output_file = (
    PROCESSED / "food_retail_clean.geojson"
)

food_retail_clean.to_file(
    output_file,
    driver="GeoJSON"
)


# =========================
# RESULTS
# =========================

print("\n=========================")
print("GROCERY CLEANING COMPLETE")
print("=========================")

print(
    "Original features:",
    len(food_retail)
)

print(
    "Clean features:",
    len(food_retail_clean)
)

print(
    "\nSaved to:",
    output_file
)