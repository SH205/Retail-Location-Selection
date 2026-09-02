import os
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "final_site_selection.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "validated_site_selection.csv"
)

TOP_N = 20


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 50)
print("SITE SELECTION VALIDATION")
print("=" * 50)

df = pd.read_csv(INPUT_FILE)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# BASIC VALIDATION
# ============================================================

print("\n" + "=" * 50)
print("BASIC VALIDATION")
print("=" * 50)

required_columns = [
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles",
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score",
    "site_selection_score",
    "site_category",
    "site_rank"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

print("Required columns: PASS")

print(f"GEOID missing: {df['GEOID'].isna().sum()}")
print(
    f"Site score missing: "
    f"{df['site_selection_score'].isna().sum()}"
)

duplicate_geoid = df["GEOID"].duplicated().sum()

print(f"Duplicate GEOIDs: {duplicate_geoid}")


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print("\n" + "=" * 50)
print("NUMERIC VALIDATION")
print("=" * 50)

numeric_columns = [
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles",
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score",
    "site_selection_score"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

print("Numeric conversion: PASS")


# ============================================================
# CHECK SCORE RANGES
# ============================================================

print("\n" + "=" * 50)
print("SCORE RANGE VALIDATION")
print("=" * 50)

score_columns = [
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score",
    "site_selection_score"
]

for col in score_columns:

    minimum = df[col].min()
    maximum = df[col].max()

    valid = (
        df[col].between(0, 1).all()
    )

    status = "PASS" if valid else "WARNING"

    print(
        f"{col}: "
        f"min={minimum:.4f}, "
        f"max={maximum:.4f} "
        f"[{status}]"
    )


# ============================================================
# CHECK FOR NEGATIVE VALUES
# ============================================================

print("\n" + "=" * 50)
print("NEGATIVE VALUE CHECK")
print("=" * 50)

non_negative_columns = [
    "Population",
    "median_income",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles"
]

for col in non_negative_columns:

    negative_count = (
        df[col] < 0
    ).sum()

    status = "PASS" if negative_count == 0 else "WARNING"

    print(
        f"{col}: "
        f"{negative_count} negative values "
        f"[{status}]"
    )


# ============================================================
# TOP 20 LOCATIONS
# ============================================================

print("\n" + "=" * 50)
print("TOP 20 LOCATIONS")
print("=" * 50)

top_sites = (
    df.sort_values(
        "site_selection_score",
        ascending=False
    )
    .head(TOP_N)
    .copy()
)

display_columns = [
    "site_rank",
    "GEOID",
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles",
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score",
    "site_selection_score",
    "site_category"
]

print(
    top_sites[display_columns].to_string(
        index=False
    )
)


# ============================================================
# WHY DO TOP SITES RANK HIGH?
# ============================================================

print("\n" + "=" * 50)
print("TOP SITE EXPLANATIONS")
print("=" * 50)

for _, row in top_sites.head(10).iterrows():

    print(
        f"\nRank #{int(row['site_rank'])} "
        f"| GEOID: {row['GEOID']}"
    )

    print(
        f"Score: "
        f"{row['site_selection_score']:.3f}"
    )

    print(
        f"Population: "
        f"{row['Population']:,.0f}"
    )

    print(
        f"Median income: "
        f"${row['median_income']:,.0f}"
    )

    print(
        f"Grocery stores: "
        f"{row['grocery_stores']:.0f}"
    )

    print(
        f"Major retailers: "
        f"{row['major_retailers']:.0f}"
    )

    print(
        f"Nearest grocery store: "
        f"{row['nearest_grocery_miles']:.2f} miles"
    )

    print(
        f"Demand score: "
        f"{row['demand_score']:.3f}"
    )

    print(
        f"Competition score: "
        f"{row['competition_score']:.3f}"
    )

    print(
        f"Accessibility score: "
        f"{row['accessibility_score_final']:.3f}"
    )

    print(
        f"Underserved score: "
        f"{row['underserved_score']:.3f}"
    )


# ============================================================
# CATEGORY DISTRIBUTION
# ============================================================

print("\n" + "=" * 50)
print("SITE CATEGORY DISTRIBUTION")
print("=" * 50)

category_counts = (
    df["site_category"]
    .value_counts()
)

print(category_counts.to_string())


# ============================================================
# SCORE STATISTICS
# ============================================================

print("\n" + "=" * 50)
print("SCORE STATISTICS")
print("=" * 50)

print(
    df["site_selection_score"]
    .describe()
    .to_string()
)


# ============================================================
# OUTLIER CHECK
# ============================================================

print("\n" + "=" * 50)
print("OUTLIER CHECK")
print("=" * 50)

q1 = df["site_selection_score"].quantile(0.25)
q3 = df["site_selection_score"].quantile(0.75)

iqr = q3 - q1

lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

outliers = df[
    (df["site_selection_score"] < lower_bound)
    |
    (df["site_selection_score"] > upper_bound)
]

print(f"Lower bound: {lower_bound:.4f}")
print(f"Upper bound: {upper_bound:.4f}")
print(f"Potential outliers: {len(outliers)}")


# ============================================================
# CORRELATION CHECK
# ============================================================

print("\n" + "=" * 50)
print("CORRELATION WITH SITE SCORE")
print("=" * 50)

correlation_columns = [
    "Population",
    "median_income",
    "poverty_rate",
    "grocery_stores",
    "apartment_count",
    "major_retailers",
    "nearest_grocery_miles",
    "nearest_road_miles",
    "demand_score",
    "competition_score",
    "accessibility_score_final",
    "underserved_score"
]

correlations = (
    df[correlation_columns + ["site_selection_score"]]
    .corr()["site_selection_score"]
    .drop("site_selection_score")
    .sort_values(
        ascending=False
    )
)

print(correlations.to_string())


# ============================================================
# TOP 20 CSV
# ============================================================

TOP_OUTPUT = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "top_20_site_locations.csv"
)

top_sites.to_csv(
    TOP_OUTPUT,
    index=False
)


# ============================================================
# SAVE VALIDATED DATA
# ============================================================

df = df.sort_values(
    "site_selection_score",
    ascending=False
).reset_index(drop=True)

df["validated_rank"] = (
    df.index + 1
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n" + "=" * 50)
print("FINAL VALIDATION")
print("=" * 50)

print(
    f"GEOID missing: "
    f"{df['GEOID'].isna().sum()}"
)

print(
    f"Score missing: "
    f"{df['site_selection_score'].isna().sum()}"
)

print(
    f"Duplicate GEOIDs: "
    f"{df['GEOID'].duplicated().sum()}"
)

print(
    f"Score minimum: "
    f"{df['site_selection_score'].min():.4f}"
)

print(
    f"Score maximum: "
    f"{df['site_selection_score'].max():.4f}"
)

print("\n" + "=" * 50)
print("VALIDATION COMPLETE")
print("=" * 50)

print(f"\nSaved:")
print(OUTPUT_FILE)
print(TOP_OUTPUT)

print("\nAnalysis complete!")
