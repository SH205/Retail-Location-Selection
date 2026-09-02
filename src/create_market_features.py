import geopandas as gpd
import pandas as pd
from pathlib import Path


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"

TRACT_FILE = PROCESSED / "orlando_census_acs.geojson"

FOOD_FILE = PROCESSED / "food_retail_clean.geojson"
APARTMENT_FILE = RAW / "Data_geojson" / "Orlando_Apartments.geojson"
RETAILER_FILE = RAW / "Data_geojson" / "Orlando_Major_Retailers.geojson"
ROAD_FILE = RAW / "Data_geojson" / "Orlando_Primary_Roads.geojson"


# =========================
# LOAD DATA
# =========================

print("=========================")
print("MARKET FEATURE CREATION")
print("=========================")

tracts = gpd.read_file(TRACT_FILE)

food_retail = gpd.read_file(FOOD_FILE)

apartments = gpd.read_file(APARTMENT_FILE)

major_retailers = gpd.read_file(RETAILER_FILE)

roads = gpd.read_file(ROAD_FILE)


print("Tracts:", len(tracts))
print("Grocery stores:", len(food_retail))
print("Apartments:", len(apartments))
print("Major retailers:", len(major_retailers))
print("Road segments:", len(roads))


# =========================
# VALIDATE GEOID
# =========================

if "GEOID" not in tracts.columns:
    raise ValueError(
        "GEOID is missing from the Census/ACS dataset."
    )


# =========================
# MATCH CRS
# =========================

food_retail = food_retail.to_crs(tracts.crs)
apartments = apartments.to_crs(tracts.crs)
major_retailers = major_retailers.to_crs(tracts.crs)
roads = roads.to_crs(tracts.crs)


# =========================
# GROCERY STORES
# =========================

grocery_join = gpd.sjoin(
    food_retail,
    tracts[["GEOID", "geometry"]],
    predicate="within",
    how="inner"
)

grocery_count = (
    grocery_join
    .groupby("GEOID")
    .size()
    .reset_index(name="grocery_stores")
)

tracts = tracts.drop(
    columns=["grocery_stores"],
    errors="ignore"
)

tracts = tracts.merge(
    grocery_count,
    on="GEOID",
    how="left"
)

tracts["grocery_stores"] = (
    tracts["grocery_stores"]
    .fillna(0)
)


# =========================
# APARTMENTS
# =========================

apartment_join = gpd.sjoin(
    apartments,
    tracts[["GEOID", "geometry"]],
    predicate="within",
    how="inner"
)

apartment_count = (
    apartment_join
    .groupby("GEOID")
    .size()
    .reset_index(name="apartment_count")
)

tracts = tracts.drop(
    columns=["apartment_count"],
    errors="ignore"
)

tracts = tracts.merge(
    apartment_count,
    on="GEOID",
    how="left"
)

tracts["apartment_count"] = (
    tracts["apartment_count"]
    .fillna(0)
)


# =========================
# MAJOR RETAILERS
# =========================

retailer_join = gpd.sjoin(
    major_retailers,
    tracts[["GEOID", "geometry"]],
    predicate="within",
    how="inner"
)

retailer_count = (
    retailer_join
    .groupby("GEOID")
    .size()
    .reset_index(name="major_retailers")
)

tracts = tracts.drop(
    columns=["major_retailers"],
    errors="ignore"
)

tracts = tracts.merge(
    retailer_count,
    on="GEOID",
    how="left"
)

tracts["major_retailers"] = (
    tracts["major_retailers"]
    .fillna(0)
)


# =========================
# ROAD ACCESS
# =========================

road_join = gpd.sjoin(
    roads,
    tracts[["GEOID", "geometry"]],
    predicate="intersects",
    how="inner"
)

road_count = (
    road_join
    .groupby("GEOID")
    .size()
    .reset_index(name="major_road_segments")
)

tracts = tracts.drop(
    columns=["major_road_segments"],
    errors="ignore"
)

tracts = tracts.merge(
    road_count,
    on="GEOID",
    how="left"
)

tracts["major_road_segments"] = (
    tracts["major_road_segments"]
    .fillna(0)
)


# =========================
# CONVERT NUMERIC FIELDS
# =========================

numeric_columns = [
    "population_B01003_001E",
    "income_B19013_001E",
    "poverty_B17001_001E",
    "housing_B25001_001E",
]

for column in numeric_columns:

    if column in tracts.columns:

        tracts[column] = pd.to_numeric(
            tracts[column],
            errors="coerce"
        )


# =========================
# STANDARDIZE MAIN VARIABLES
# =========================

if "population_B01003_001E" in tracts.columns:
    tracts["Population"] = tracts[
        "population_B01003_001E"
    ]

if "income_B19013_001E" in tracts.columns:
    tracts["median_income"] = tracts[
        "income_B19013_001E"
    ]

if "housing_B25001_001E" in tracts.columns:
    tracts["housing_units"] = tracts[
        "housing_B25001_001E"
    ]


# =========================
# POVERTY RATE
# =========================

poverty_columns = [
    column for column in tracts.columns
    if column.startswith("poverty_")
    and column.endswith("E")
]

if len(poverty_columns) >= 2:

    poverty_values = []

    for column in poverty_columns:

        tracts[column] = pd.to_numeric(
            tracts[column],
            errors="coerce"
        )

        poverty_values.append(column)

    # B17001 total population for whom poverty
    # status is determined
    total_candidates = [
        column for column in poverty_columns
        if column.endswith("001E")
    ]

    total_column = (
        total_candidates[0]
        if total_candidates
        else None
    )

    # Find below-poverty population
    below_candidates = [
        column for column in poverty_columns
        if "002E" in column
    ]

    below_column = (
        below_candidates[0]
        if below_candidates
        else None
    )

    if total_column and below_column:

        tracts["poverty_rate"] = (
            tracts[below_column] /
            tracts[total_column].replace(0, pd.NA)
        ) * 100

    else:
        tracts["poverty_rate"] = pd.NA

else:

    tracts["poverty_rate"] = pd.NA


# =========================
# POPULATION DENSITY
# =========================

tracts["area_sq_miles"] = (
    pd.to_numeric(
        tracts["ALAND"],
        errors="coerce"
    ) / 2589988.11
)

tracts["population_density"] = (
    tracts["Population"] /
    tracts["area_sq_miles"].replace(0, pd.NA)
)


# =========================
# GROCERY DENSITY
# =========================

tracts["grocery_stores_per_1000"] = (
    tracts["grocery_stores"] /
    tracts["Population"].replace(0, pd.NA)
) * 1000


# =========================
# NORMALIZED SCORES
# =========================

tracts["population_score"] = (
    tracts["Population"].rank(pct=True)
)

tracts["income_score"] = (
    tracts["median_income"].rank(pct=True)
)

tracts["apartment_score"] = (
    tracts["apartment_count"].rank(pct=True)
)

tracts["competition_score"] = (
    1 - tracts["grocery_stores"].rank(pct=True)
)

tracts["road_access_score"] = (
    tracts["major_road_segments"].rank(pct=True)
)


# =========================
# OPPORTUNITY SCORE
# =========================

tracts["opportunity_score"] = (
    tracts["population_score"] * 0.25
    + tracts["income_score"] * 0.15
    + tracts["apartment_score"] * 0.20
    + tracts["competition_score"] * 0.25
    + tracts["road_access_score"] * 0.15
)


# =========================
# LOCATION RANK
# =========================

tracts["location_rank"] = (
    tracts["opportunity_score"]
    .rank(method="min", ascending=False)
)

tracts["location_rank"] = (
    tracts["location_rank"]
    .fillna(len(tracts) + 1)
    .astype(int)
)

# =========================
# FINAL COLUMNS
# =========================

final_columns = [
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "housing_units",
    "population_density",
    "grocery_stores",
    "grocery_stores_per_1000",
    "apartment_count",
    "major_retailers",
    "major_road_segments",
    "population_score",
    "income_score",
    "apartment_score",
    "competition_score",
    "road_access_score",
    "opportunity_score",
    "location_rank",
    "geometry"
]

# Keep only columns that exist
final_columns = [
    column
    for column in final_columns
    if column in tracts.columns
]

final_data = tracts[
    final_columns
].copy()


# =========================
# SORT
# =========================

final_data = final_data.sort_values(
    "location_rank"
)


# =========================
# SAVE GEOJSON
# =========================

geojson_output = (
    PROCESSED /
    "final_market_features.geojson"
)

final_data.to_file(
    geojson_output,
    driver="GeoJSON"
)


# =========================
# SAVE CSV
# =========================

csv_output = (
    PROCESSED /
    "final_market_features.csv"
)

final_data.drop(
    columns="geometry"
).to_csv(
    csv_output,
    index=False
)


# =========================
# DISPLAY RESULTS
# =========================

print("\n=========================")
print("TOP 20 RETAIL LOCATIONS")
print("=========================")

display_columns = [
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

print(
    final_data[
        display_columns
    ]
    .head(20)
    .to_string(index=False)
)


print("\n=========================")
print("FINAL DATASET")
print("=========================")

print("Rows:", len(final_data))
print("Columns:", len(final_data.columns))

print("\nSaved:")
print(geojson_output)
print(csv_output)

print("\nAnalysis complete!")