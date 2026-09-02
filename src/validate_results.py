import pandas as pd
from pathlib import Path

# =========================
# FILE LOCATIONS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED / "top_retail_locations.csv"


# =========================
# LOAD RESULTS
# =========================

results = pd.read_csv(INPUT_FILE)

print("\n=========================")
print("RETAIL LOCATION VALIDATION")
print("=========================")

print(f"Rows: {len(results)}")
print(f"Columns: {len(results.columns)}")


# =========================
# CHECK MISSING VALUES
# =========================

print("\nMissing values:")

missing = results.isnull().sum()

print(
    missing[missing > 0]
    if missing.sum() > 0
    else "No missing values!"
)


# =========================
# CHECK DUPLICATE TRACTS
# =========================

print("\nDuplicate GEOIDs:")

duplicates = results["GEOID"].duplicated().sum()

print(duplicates)


# =========================
# TOP 20 LOCATIONS
# =========================

print("\n=========================")
print("TOP 20 CANDIDATE LOCATIONS")
print("=========================")

columns = [
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "major_road_segments",
    "opportunity_score"
]

print(
    results[columns]
    .head(20)
    .to_string(index=False)
)


# =========================
# SUMMARY STATISTICS
# =========================

print("\n=========================")
print("SUMMARY STATISTICS")
print("=========================")

print(
    results[
        [
            "Population",
            "median_income",
            "poverty_rate",
            "grocery_stores",
            "apartment_count",
            "major_retailers",
            "major_road_segments",
            "opportunity_score"
        ]
    ].describe()
)


# =========================
# CHECK SCORE RANGE
# =========================

print("\n=========================")
print("OPPORTUNITY SCORE")
print("=========================")

print(
    f"Minimum: {results['opportunity_score'].min():.3f}"
)

print(
    f"Maximum: {results['opportunity_score'].max():.3f}"
)

print(
    f"Average: {results['opportunity_score'].mean():.3f}"
)


# =========================
# CHECK OUTLIERS
# =========================

print("\n=========================")
print("POTENTIAL OUTLIERS")
print("=========================")

print("\nHighest grocery competition:")

print(
    results[
        [
            "GEOID",
            "grocery_stores",
            "Population"
        ]
    ]
    .sort_values(
        "grocery_stores",
        ascending=False
    )
    .head(5)
    .to_string(index=False)
)

print("\nHighest apartment concentration:")

print(
    results[
        [
            "GEOID",
            "apartment_count",
            "Population"
        ]
    ]
    .sort_values(
        "apartment_count",
        ascending=False
    )
    .head(5)
    .to_string(index=False)
)


# =========================
# FINAL CHECK
# =========================

print("\n=========================")
print("VALIDATION COMPLETE")
print("=========================")