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
# LOAD CENSUS TRACTS
# =========================

census_file = (
    RAW
    / "FL_Census_Tract_ 2024"
    / "tl_2024_12_tract.shp"
)

tracts = gpd.read_file(census_file)


print("=========================")
print("CENSUS TRACT PROCESSING")
print("=========================")

print("Total Florida tracts:", len(tracts))


# =========================
# KEEP ORANGE COUNTY AREA
# =========================

# Orlando-area project uses Orange County.
# Orange County FIPS = 095

tracts = tracts[
    tracts["COUNTYFP"] == "095"
].copy()


# =========================
# VALIDATE GEOID
# =========================

if "GEOID" not in tracts.columns:
    raise ValueError("GEOID is missing from Census tract data.")

print("Orange County tracts:", len(tracts))


# =========================
# SAVE
# =========================

output_file = (
    PROCESSED / "orlando_census_tracts.geojson"
)

tracts.to_file(
    output_file,
    driver="GeoJSON"
)


# =========================
# RESULTS
# =========================

print("\n=========================")
print("CENSUS TRACTS COMPLETE")
print("=========================")

print("Rows:", len(tracts))
print("Columns:", list(tracts.columns))

print("\nSaved:")
print(output_file)