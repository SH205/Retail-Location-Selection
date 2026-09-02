import geopandas as gpd
import pandas as pd
from pathlib import Path


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"

TRACT_FILE = PROCESSED / "orlando_census_tracts.geojson"


# =========================
# LOAD CENSUS TRACTS
# =========================

print("=========================")
print("MERGING ACS DATA")
print("=========================")

tracts = gpd.read_file(TRACT_FILE)

print("Census tracts:", len(tracts))


# =========================
# ACS FILES
# =========================

acs_files = {
    "population": RAW / "ACSDT5Y2024.B01003 — Population" /
                  "ACS_2024_B01003_Population.csv",

    "income": RAW / "ACS_5Y2024_ B19013  — Median household income" /
              "B19013-Data.csv",

    "poverty": RAW / "ACSDT5Y2024.B17001 — Poverty" /
               "ACSDT5Y2024.B17001-Data.csv",

    "housing": RAW / "ACSDT5Y2024.B25001 — Housing units" /
               "ACSDT5Y2024.B25001-Data.csv",

    "households": RAW / "ACSDT5Y2024.B11001 — Household characteristics" /
                  "ACSDT5Y2024.B11001-Data.csv"
}


# =========================
# LOAD FIRST FILE
# =========================

population = pd.read_csv(
    acs_files["population"],
    dtype=str
)

print("\nPopulation columns:")
print(population.columns.tolist())


# =========================
# FIND GEOID
# =========================

def find_geoid(df):

    for col in ["GEO_ID", "GEOID", "Geography"]:
        if col in df.columns:
            return col

    raise ValueError(
        "Could not find GEOID column. Columns are:\n"
        + str(df.columns.tolist())
    )


# =========================
# CLEAN GEOID
# =========================

def clean_geoid(df):

    geoid_col = find_geoid(df)

    df = df.rename(
        columns={geoid_col: "GEOID"}
    ).copy()

    df["GEOID"] = (
        df["GEOID"]
        .astype(str)
        .str.replace("1400000US", "", regex=False)
        .str.replace("US", "", regex=False)
        .str.strip()
    )

    return df


# =========================
# LOAD ACS TABLES
# =========================

dataframes = {}

for name, file in acs_files.items():

    print(f"\nLoading {name}...")

    df = pd.read_csv(
        file,
        dtype=str
    )

    df = clean_geoid(df)

    df = df.drop_duplicates(
        subset=["GEOID"]
    )

    dataframes[name] = df

    print("Rows:", len(df))


# =========================
# START WITH TRACTS
# =========================

result = tracts.copy()

result["GEOID"] = (
    result["GEOID"]
    .astype(str)
    .str.strip()
)


# =========================
# MERGE ACS TABLES
# =========================

for name, df in dataframes.items():

    print(f"Merging {name}...")

    # Remove Geography name columns
    drop_columns = [
        col for col in df.columns
        if col.lower() in [
            "name",
            "geography"
        ]
    ]

    df = df.drop(
        columns=drop_columns,
        errors="ignore"
    )

    # Rename non-GEOID columns
    rename_dict = {}

    for col in df.columns:

        if col != "GEOID":
            rename_dict[col] = f"{name}_{col}"

    df = df.rename(
        columns=rename_dict
    )

    result = result.merge(
        df,
        on="GEOID",
        how="left"
    )


# =========================
# VALIDATION
# =========================

print("\n=========================")
print("ACS MERGE COMPLETE")
print("=========================")

print("Rows:", len(result))
print("Columns:", len(result.columns))

print("\nGEOID missing:",
      result["GEOID"].isna().sum())


# =========================
# SAVE
# =========================

output_file = (
    PROCESSED / "orlando_census_acs.geojson"
)

result.to_file(
    output_file,
    driver="GeoJSON"
)


print("\nSaved:")
print(output_file)