import pandas as pd
from pathlib import Path


# File locations
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "census_market_data.csv"

# Load cleaned Census files
population = pd.read_csv(PROCESSED_DIR / "population_clean.csv")
income = pd.read_csv(PROCESSED_DIR / "income_clean.csv")
poverty = pd.read_csv(PROCESSED_DIR / "poverty_clean.csv")
housing = pd.read_csv(PROCESSED_DIR / "housing_clean.csv")
owner_renter = pd.read_csv(PROCESSED_DIR / "owner_renter_clean.csv")
vehicles = pd.read_csv(PROCESSED_DIR / "vehicles_clean.csv")
households = pd.read_csv(PROCESSED_DIR / "household_clean.csv")

# Combine the Census datasets
census = population
census = census.merge(income, on="geo_id", how="left", suffixes=("", "_income"))
census = census.merge(poverty, on="geo_id", how="left", suffixes=("", "_poverty"))
census = census.merge(housing, on="geo_id", how="left", suffixes=("", "_housing"))
census = census.merge(owner_renter, on="geo_id", how="left", suffixes=("", "_owner_renter"))
census = census.merge(vehicles, on="geo_id", how="left", suffixes=("", "_vehicles"))
census = census.merge(households, on="geo_id", how="left", suffixes=("", "_households"))

# Remove duplicate census tracts
census = census.drop_duplicates()

census.to_csv(OUTPUT_FILE, index=False)

print(f"Rows: {len(census):,}")
print(f"Columns: {len(census.columns):,}")
print(f"Saved to: {OUTPUT_FILE}")

