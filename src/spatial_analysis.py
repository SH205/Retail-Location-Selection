import pandas as pd
import geopandas as gpd
from pathlib import Path

# FILE LOCATIONS
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"
RAW = BASE_DIR / "data" / "raw"

# LOAD CENSUS DATA
census = pd.read_csv(PROCESSED / "census_market_data.csv")

print("Census data:")
print(census.shape)
print(census.head())


# LOAD TIGER/LINE
# =========================

tracts = gpd.read_file( RAW / "FL_Census_Tract_ 2024" / "tl_2024_12_tract.shp")

# Filter to Orange County (FIPS code 095)
tracts = tracts[tracts["COUNTYFP"] == "095"]

print("\nCensus boundaries:")
print(tracts.shape)
print(tracts.head())

# =========================
# STANDARDIZE GEO IDs
# =========================

census["geo_id"] = census["geo_id"].astype(str)
tracts["GEOIDFQ"] = tracts["GEOIDFQ"].astype(str)


# =========================
# MERGE CENSUS + MAP
# =========================

tracts = tracts.merge(
    census,
    left_on="GEOIDFQ",
    right_on="geo_id",
    how="inner"
)

print("\nMerged data:")
print(tracts.shape)
print(tracts.head())



# Load Data
food_retail = gpd.read_file( RAW / "Data_geojson" / "Orlando_Food_Retail.geojson")
major_retailers = gpd.read_file( RAW / "Data_geojson" / "Orlando_Major_Retailers.geojson")
apartments = gpd.read_file(RAW / "Data_geojson" / "Orlando_Apartments.geojson")
motorways = gpd.read_file(RAW / "Data_geojson" / "Orlando_Motorways:Trunk_Roads.geojson")
primary_roads = gpd.read_file( RAW / "Data_geojson" / "Orlando_Primary_Roads.geojson")



# Match COORDINATE System

tracts = tracts.to_crs(epsg=32617)

food_retail = food_retail.to_crs(tracts.crs)
major_retailers = major_retailers.to_crs(tracts.crs)
apartments = apartments.to_crs(tracts.crs)
motorways = motorways.to_crs(tracts.crs)
primary_roads = primary_roads.to_crs(tracts.crs)


# Grocery Store Count BY TRACT
# =========================
grocery_count = gpd.sjoin(
    food_retail,
    tracts[["GEOID", "geometry"]],
    predicate="within"
)

grocery_count = (
    grocery_count
    .groupby("GEOID")
    .size()
    .reset_index(name="grocery_stores")
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


# Calculate grocery stores per 1,000 people
# =========================
tracts["grocery_stores_per_1000"] = (
    tracts["grocery_stores"] /
    tracts["Population"] * 1000
)


# Calculate population density
# =========================
tracts["area_sq_miles"] = (
    tracts.geometry.area / 2_589_988.11
)

tracts["population_density"] = (
    tracts["Population"] /
    tracts["area_sq_miles"]
)


# Calculate poverty rate
# =========================
tracts["poverty_rate"] = (
    tracts["Below poverty level"] /
    tracts["Poverty"] * 100
)

print("\nPoverty rate calculated:")
print(tracts[[
    "GEOID",
    "Poverty",
    "Below poverty level",
    "At or above poverty level",
    "poverty_rate"
]].head())

# APARTMENTS BY TRACT
# =========================
apartment_count = gpd.sjoin(
    apartments,
    tracts[["GEOID", "geometry"]],
    predicate="within"
)

apartment_count = (
    apartment_count
    .groupby("GEOID")
    .size()
    .reset_index(name="apartment_count")
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

# MAJOR RETAILERS BY TRACT
# =========================

retailer_count = gpd.sjoin(
    major_retailers,
    tracts[["GEOID", "geometry"]],
    predicate="within"
)

retailer_count = (
    retailer_count
    .groupby("GEOID")
    .size()
    .reset_index(name="major_retailers")
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

print("Tracts with major retailers:",
      (tracts["major_retailers"] > 0).sum())




# ROAD ACCESSIBILITY BY TRACT
# =========================

# Combine major roads
roads = pd.concat([
    motorways,
    primary_roads
], ignore_index=True)

# Convert back to GeoDataFrame
roads = gpd.GeoDataFrame(
    roads,
    geometry="geometry",
    crs=motorways.crs
)

# Count road segments in each tract
road_count = gpd.sjoin(
    roads,
    tracts[["GEOID", "geometry"]],
    predicate="intersects"
)

road_count = (
    road_count
    .groupby("GEOID")
    .size()
    .reset_index(name="major_road_segments")
)

# Add road count to tracts
tracts = tracts.merge(
    road_count,
    on="GEOID",
    how="left"
)

tracts["major_road_segments"] = (
    tracts["major_road_segments"]
    .fillna(0)
)

# Accessibility score
tracts["road_access_score"] = (
    tracts["major_road_segments"]
    .rank(pct=True)
)

print("\nRoad accessibility:")
print(
    tracts[
        ["GEOID", "major_road_segments", "road_access_score"]
    ].sort_values(
        "road_access_score",
        ascending=False
    ).head(10)
)

# RETAIL OPPORTUNITY SCORE
# =========================
tracts["population_score"] = (
    tracts["Population"]
    .rank(pct=True)
)

tracts["income_score"] = (
    tracts["median_income"]
    .rank(pct=True)
)

tracts["apartment_score"] = (
    tracts["apartment_count"]
    .rank(pct=True)
)

# Fewer grocery stores = better opportunity
tracts["competition_score"] = (
    1 - tracts["grocery_stores"]
    .rank(pct=True)
)

tracts["opportunity_score"] = (
    tracts["population_score"] * 0.30 +
    tracts["income_score"] * 0.20 +
    tracts["apartment_score"] * 0.20 +
    tracts["competition_score"] * 0.30
)



# Find the top locations
top_locations = tracts.sort_values(
    "opportunity_score",
    ascending=False
)

print(
    top_locations[
        [
            "GEOID",
            "Population",
            "median_income",
            "poverty_rate",
            "grocery_stores",
            "apartment_count",
            "opportunity_score"
        ]
    ].head(20)
)

# SAVE RESULTS
tracts.to_file(
    PROCESSED / "retail_market_analysis.geojson",
    driver="GeoJSON"
)

top_locations.drop(
    columns="geometry"
).to_csv(
    PROCESSED / "top_retail_locations.csv",
    index=False
)


print("Grocery stores assigned:")
print(grocery_count["grocery_stores"].describe())

print("\nApartment buildings assigned:")
print(apartment_count["apartment_count"].describe())
print("Tracts with grocery stores:",
      (tracts["grocery_stores"] > 0).sum())

print("Tracts with apartments:",
      (tracts["apartment_count"] > 0).sum())


print("\nAnalysis complete!")








# Orlando_Apartments.geojson
# Orlando_Food_Retail.geojson
# Orlando_Major_Retailers.geojson
# Orlando_Motorways:Trunk_Roads.geojson
# Orlando_Primary_Roads.geojson
#