import pandas as pd
from pathlib import Path


# PATHS
# =========================

home = Path.home()
raw = Path(home / 'Downloads/R/data/raw/')
processed = Path(home / 'Downloads/R/data/processed/')


# =========================
# CENSUS — B19013 — MEDIAN INCOME
# =========================

income = pd.read_csv(raw / 'ACS_5Y2024_ B19013  — Median household income/B19013-Data.csv', skiprows=1)

income = income.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Median household income in the past 12 months (in 2024 inflation-adjusted dollars)": "median_income"
})

# Keep only Orange County, Florida census tracts
income = income[
    income["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

income = income[
    ["geo_id", "geography", "median_income"]
]

income["median_income"] = pd.to_numeric(
    income["median_income"],
    errors="coerce"
)

income = income.dropna(
    subset=["median_income"]
)

income.to_csv(
    processed / "income_clean.csv",
    index=False
)

# FINISHED
print("Income cleaning complete!")
print(f"Rows: {len(income)}")
print(income.head())


# =========================
# CENSUS — B01003 — Population 
# =========================

Population = pd.read_csv(raw / 'ACSDT5Y2024.B01003 — Population/ACS_2024_B01003_Population.csv', skiprows=1)

Population = Population.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total": "Population"
})

# Keep only Orange County, Florida census tracts
Population = Population[
    Population["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Population = Population[
    ["geo_id", "geography", "Population"]
]

Population["Population"] = pd.to_numeric(
    Population["Population"],
    errors="coerce"
)

Population = Population.dropna(
    subset=["Population"]
)

Population.to_csv(
    processed / "population_clean.csv",
    index=False
)

# FINISHED
print("Population cleaning complete!")
print(f"Rows: {len(Population)}")
print(Population.head())


# =========================
# CENSUS — B11001 — Household characteristics
# =========================

Household = pd.read_csv(raw / 'ACSDT5Y2024.B11001 — Household characteristics/ACSDT5Y2024.B11001-Data.csv', skiprows=1)

Household = Household.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total:": "Population",
    "Estimate!!Total:!!Family households:": "Family households",
    "Estimate!!Total:!!Family households:!!Married-couple family": "Married-couple family households",
    "Estimate!!Total:!!Family households:!!Other family:": "Other family households",
    "Estimate!!Total:!!Family households:!!Other family:!!Male householder, no spouse present": "Male householder, no spouse present",
    "Estimate!!Total:!!Family households:!!Other family:!!Female householder, no spouse present": "Female householder, no spouse present",
    "Estimate!!Total:!!Nonfamily households:": "Nonfamily households",
    "Estimate!!Total:!!Nonfamily households:!!Householder living alone": "Householder living alone",
    "Estimate!!Total:!!Nonfamily households:!!Householder not living alone": "Householder not living alone"
})

# Keep only Orange County, Florida census tracts
Household = Household[
    Household["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Household = Household[
    ["geo_id", "geography", "Population", "Family households", "Married-couple family households", "Other family households", "Male householder, no spouse present", "Female householder, no spouse present", "Nonfamily households", "Householder living alone", "Householder not living alone"]
]

Household["Population"] = pd.to_numeric(
    Household["Population"],
    errors="coerce"
)

Household["Family households"] = pd.to_numeric(
    Household["Family households"],
    errors="coerce"
)

Household["Married-couple family households"] = pd.to_numeric(
    Household["Married-couple family households"],
    errors="coerce"
)

Household["Other family households"] = pd.to_numeric(
    Household["Other family households"],
    errors="coerce"
)

Household["Male householder, no spouse present"] = pd.to_numeric(
    Household["Male householder, no spouse present"],
    errors="coerce"
)

Household["Female householder, no spouse present"] = pd.to_numeric(
    Household["Female householder, no spouse present"],
    errors="coerce"
)

Household["Nonfamily households"] = pd.to_numeric(
    Household["Nonfamily households"],
    errors="coerce"
)

Household["Householder living alone"] = pd.to_numeric(
    Household["Householder living alone"],
    errors="coerce"
)

Household["Householder not living alone"] = pd.to_numeric(
    Household["Householder not living alone"],
    errors="coerce"
)

Household = Household.dropna(
    subset=["Population"]
)

Household = Household.dropna(
    subset=["Family households"]
)

Household = Household.dropna(
    subset=["Married-couple family households"]
)

Household = Household.dropna(
    subset=["Other family households"]
)

Household = Household.dropna(
    subset=["Male householder, no spouse present"]
)

Household = Household.dropna(
    subset=["Female householder, no spouse present"]
)

Household = Household.dropna(
    subset=["Nonfamily households"]
)

Household = Household.dropna(
    subset=["Householder living alone"]
)

Household = Household.dropna(
    subset=["Householder not living alone"]
)

Household.to_csv(
    processed / "household_clean.csv",
    index=False
)

# FINISHED
print("Household cleaning complete!")
print(f"Rows: {len(Household)}")
print(Household.head())


# =========================
# CENSUS — B17001 — Poverty
# =========================

Poverty = pd.read_csv(raw / 'ACSDT5Y2024.B17001 — Poverty/ACSDT5Y2024.B17001-Data.csv', skiprows=1)

Poverty = Poverty.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total": "Poverty",   
})

Poverty = Poverty.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",

    "Estimate!!Total:": "Poverty",

    "Estimate!!Total:!!Income in the past 12 months below poverty level:":
        "Below poverty level",

    "Estimate!!Total:!!Income in the past 12 months below poverty level:!!Male:":
        "Below poverty level - Male",

    "Estimate!!Total:!!Income in the past 12 months below poverty level:!!Female:":
        "Below poverty level - Female",

    "Estimate!!Total:!!Income in the past 12 months at or above poverty level:":
        "At or above poverty level",

    "Estimate!!Total:!!Income in the past 12 months at or above poverty level:!!Male:":
        "At or above poverty level - Male",

    "Estimate!!Total:!!Income in the past 12 months at or above poverty level:!!Female:":
        "At or above poverty level - Female",
})

# Remove Margin of Error columns
Poverty = Poverty.loc[
    :, ~Poverty.columns.str.startswith("Margin of Error")
]

# Remove extra column
Poverty = Poverty.drop(
    columns=["Unnamed: 120"],
    errors="ignore"
)



# Keep only Orange County, Florida census tracts
Poverty = Poverty[
    Poverty["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Poverty = Poverty[
    ["geo_id", "geography", "Poverty", "Below poverty level", "Below poverty level - Male", "Below poverty level - Female", "At or above poverty level", "At or above poverty level - Male", "At or above poverty level - Female"]
]

Poverty["Poverty"] = pd.to_numeric(
    Poverty["Poverty"],
    errors="coerce"
)

Poverty["Below poverty level"] = pd.to_numeric(
    Poverty["Below poverty level"],
    errors="coerce"
)

Poverty["At or above poverty level"] = pd.to_numeric(
    Poverty["At or above poverty level"],
    errors="coerce"
)

Poverty["Below poverty level - Male"] = pd.to_numeric(
    Poverty["Below poverty level - Male"],
    errors="coerce"
)
Poverty["Below poverty level - Female"] = pd.to_numeric(
    Poverty["Below poverty level - Female"],
    errors="coerce"
)

Poverty["At or above poverty level - Male"] = pd.to_numeric(
    Poverty["At or above poverty level - Male"],
    errors="coerce"
)

Poverty["At or above poverty level - Female"] = pd.to_numeric(
    Poverty["At or above poverty level - Female"],
    errors="coerce"
)

Poverty = Poverty.dropna(
    subset=["Poverty"]
)

Poverty = Poverty.dropna(
    subset=["Below poverty level"]
)

Poverty = Poverty.dropna(
    subset=["At or above poverty level"]
)
Poverty = Poverty.dropna(
    subset=["At or above poverty level - Male"]
)

Poverty = Poverty.dropna(
    subset=["At or above poverty level - Female"]
)

Poverty = Poverty.dropna(
    subset=["Below poverty level - Male"]
)

Poverty = Poverty.dropna(
    subset=["Below poverty level - Female"]
)

Poverty.to_csv(
    processed / "poverty_clean.csv",
    index=False
)   


# FINISHED
print("Poverty cleaning complete!")
print(f"Rows: {len(Poverty)}")
print(Poverty.head())


# =========================
# CENSUS — B25001 — Housing units 
# =========================

Housing = pd.read_csv(raw / 'ACSDT5Y2024.B25001 — Housing units/ACSDT5Y2024.B25001-Data.csv', skiprows=1)

Housing = Housing.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total": "Housing units"
})

# Keep only Orange County, Florida census tracts
Housing = Housing[
    Housing["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Housing = Housing[
    ["geo_id", "geography", "Housing units"]
]

Housing["Housing units"] = pd.to_numeric(
    Housing["Housing units"],
    errors="coerce"
)

Housing = Housing.dropna(
    subset=["Housing units"]
)

Housing.to_csv(
    processed / "housing_clean.csv",
    index=False
)

# FINISHED
print("Housing cleaning complete!")
print(f"Rows: {len(Housing)}")
print(Housing.head())


# =========================
# CENSUS — B25003 — Owner:renter occupancy 
# =========================

Owner_renter = pd.read_csv(raw / 'ACSDT5Y2024.B25003 — Owner:renter occupancy/ACSDT5Y2024.B25003-Data.csv', skiprows=1)

Owner_renter = Owner_renter.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total:": "Owner:renter occupancy",
    "Estimate!!Total:!!Owner occupied": "Owner occupied",
    "Estimate!!Total:!!Renter occupied": "Renter occupied"
})
# Keep only Orange County, Florida census tracts
Owner_renter = Owner_renter[
    Owner_renter["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Owner_renter = Owner_renter[
    ["geo_id", "geography", "Owner:renter occupancy", "Owner occupied", "Renter occupied"]
]

Owner_renter["Owner:renter occupancy"] = pd.to_numeric(
    Owner_renter["Owner:renter occupancy"],
    errors="coerce"
)

Owner_renter["Owner occupied"] = pd.to_numeric(
    Owner_renter["Owner occupied"],
    errors="coerce"
)

Owner_renter["Renter occupied"] = pd.to_numeric(
    Owner_renter["Renter occupied"],
    errors="coerce"
)

Owner_renter = Owner_renter.dropna(
    subset=["Owner:renter occupancy"]
)

Owner_renter = Owner_renter.dropna(
    subset=["Owner occupied"]
)

Owner_renter = Owner_renter.dropna(
    subset=["Renter occupied"]
)

Owner_renter.to_csv(
    processed / "owner_renter_clean.csv",
    index=False
)

# FINISHED
print("Owner:renter occupancy cleaning complete!")
print(f"Rows: {len(Owner_renter)}")
print(Owner_renter.head())


# =========================
# CENSUS — B25044 — Vehicles available 
# =========================

Vehicles = pd.read_csv(raw / 'ACSDT5Y2024.B25044 — Vehicles available/ACSDT5Y2024.B25044-Data.csv', skiprows=1)

Vehicles = Vehicles.rename(columns={
    "Geography": "geo_id",
    "Geographic Area Name": "geography",
    "Estimate!!Total:": "Vehicles available",

    "Estimate!!Total:!!Owner occupied:": "Owner occupied",
    "Estimate!!Total:!!Owner occupied:!!No vehicle available": "Owner occupied - No vehicles available",
    "Estimate!!Total:!!Owner occupied:!!1 vehicle available": "Owner occupied - 1 vehicle available",

    "Estimate!!Total:!!Renter occupied:": "Renter occupied",
    "Estimate!!Total:!!Renter occupied:!!No vehicle available": "Renter occupied - No vehicles available",
    "Estimate!!Total:!!Renter occupied:!!1 vehicle available": "Renter occupied - 1 vehicle available",

})

# Keep only Orange County, Florida census tracts
Vehicles = Vehicles[
    Vehicles["geography"].str.contains(
        "Orange County; Florida",
        na=False
    )
]

Vehicles = Vehicles[
    ["geo_id", "geography", "Vehicles available", "Owner occupied", "Owner occupied - No vehicles available", "Owner occupied - 1 vehicle available", "Renter occupied", "Renter occupied - No vehicles available", "Renter occupied - 1 vehicle available"]
]

Vehicles["Vehicles available"] = pd.to_numeric(
    Vehicles["Vehicles available"],
    errors="coerce"
)

Vehicles["Owner occupied"] = pd.to_numeric(
    Vehicles["Owner occupied"],
    errors="coerce"
)
Vehicles["Owner occupied - No vehicles available"] = pd.to_numeric(
    Vehicles["Owner occupied - No vehicles available"],
    errors="coerce"
)
Vehicles["Owner occupied - 1 vehicle available"] = pd.to_numeric(
    Vehicles["Owner occupied - 1 vehicle available"],
    errors="coerce"
)
Vehicles["Renter occupied"] = pd.to_numeric(
    Vehicles["Renter occupied"],
    errors="coerce"
)
Vehicles["Renter occupied - No vehicles available"] = pd.to_numeric(
    Vehicles["Renter occupied - No vehicles available"],
    errors="coerce"
)
Vehicles["Renter occupied - 1 vehicle available"] = pd.to_numeric(
    Vehicles["Renter occupied - 1 vehicle available"],
    errors="coerce"
)

Vehicles = Vehicles.dropna(subset=["Vehicles available"])
Vehicles = Vehicles.dropna(subset=["Owner occupied"])
Vehicles = Vehicles.dropna(subset=["Owner occupied - No vehicles available"])
Vehicles = Vehicles.dropna(subset=["Owner occupied - 1 vehicle available"])
Vehicles = Vehicles.dropna(subset=["Renter occupied"])
Vehicles = Vehicles.dropna(subset=["Renter occupied - No vehicles available"])   
Vehicles = Vehicles.dropna(subset=["Renter occupied - 1 vehicle available"])


Vehicles.to_csv(
    processed / "vehicles_clean.csv",
    index=False
)

# FINISHED
print("Vehicles cleaning complete!")
print(f"Rows: {len(Vehicles)}")
print(Vehicles.head())
