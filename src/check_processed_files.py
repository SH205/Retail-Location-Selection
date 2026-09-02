import geopandas as gpd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"

print("\nFILES IN PROCESSED:")
print("=========================")

for file in PROCESSED.glob("*.geojson"):

    print("\nFILE:", file.name)

    gdf = gpd.read_file(file)

    print("Rows:", len(gdf))
    print("Columns:", list(gdf.columns))

    if "GEOID" in gdf.columns:
        print("✅ GEOID FOUND")
    else:
        print("❌ GEOID MISSING")