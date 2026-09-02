import geopandas as gpd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"

print("\n=========================")
print("SEARCHING FOR CENSUS DATA")
print("=========================")

for folder in [RAW, PROCESSED]:

    print(f"\nFOLDER: {folder}")

    for file in folder.rglob("*"):

        if file.suffix.lower() in [".geojson", ".shp", ".gpkg"]:

            try:
                gdf = gpd.read_file(file)

                print(
                    f"\n{file.relative_to(BASE_DIR)}"
                )

                print("Rows:", len(gdf))
                print("Columns:", list(gdf.columns))

                if "GEOID" in gdf.columns:
                    print(">>> ✅ GEOID FOUND <<<")

            except Exception as e:
                print(
                    f"Could not read {file.name}: {e}"
                )