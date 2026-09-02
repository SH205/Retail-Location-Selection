import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium import Element
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

FINAL = BASE / "data/processed/final_site_selection.geojson"
GROCERY = BASE / "data/processed/food_retail_clean.geojson"
MAJOR = BASE / "data/raw/Data_geojson/Orlando_Major_Retailers.geojson"
ROADS = BASE / "data/raw/Data_geojson/Orlando_Primary_Roads.geojson"
OUTPUT = BASE / "data/processed/orlando_site_selection_map.html"


WGS84 = "EPSG:4326"
UTM = "EPSG:32617"
COMP_RADIUS = 1.0
MAX_ROAD_MILES = 0.75
MIN_ROAD_MILES = 0.01  # Require at least some road access
MAX_MARKERS_DEFAULT = 20  # Default maximum number of markers to show


def load(path):
    if not os.path.exists(path):
        return None

    x = gpd.read_file(path)

    if x.crs is None:
        x = x.set_crs(WGS84)

    return x.to_crs(WGS84)


def num(df, col, default=0):
    if col not in df:
        return pd.Series(default, index=df.index, dtype=float)

    return pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(default)


def nearest_miles(points, targets):
    if targets is None or len(targets) == 0:
        return pd.Series(
            np.inf,
            index=points.index
        )

    p = points.to_crs(UTM)
    t = targets.to_crs(UTM)

    j = gpd.sjoin_nearest(
        p[["geometry"]],
        t[["geometry"]],
        how="left",
        distance_col="_dist"
    )

    d = j.groupby(j.index)["_dist"].min()

    return (
        d.reindex(points.index)
        .fillna(np.inf)
        / 1609.344
    )


def count_radius(points, targets, miles):
    if targets is None or len(targets) == 0:
        return pd.Series(
            0,
            index=points.index,
            dtype=int
        )

    p = points.to_crs(UTM)
    t = targets.to_crs(UTM)

    j = gpd.sjoin(
        p[["geometry"]],
        t[["geometry"]],
        how="left",
        predicate="dwithin",
        distance=miles * 1609.344
    )

    counts = j.groupby(j.index).size()

    return (
        counts
        .reindex(points.index)
        .fillna(0)
        .astype(int)
    )


print("=" * 70)
print("INTERACTIVE ORLANDO SITE SELECTION MAP")
print("=" * 70)


# ------------------------------------------------------------
# Loading data
# ------------------------------------------------------------

print("\nLoading data...")

sites = gpd.read_file(FINAL).to_crs(WGS84)
sites["GEOID"] = sites["GEOID"].astype(str)

grocery = load(GROCERY)
major = load(MAJOR)
roads = load(ROADS)

print(f"Tracts: {len(sites)}")
print(
    f"Grocery stores: "
    f"{len(grocery) if grocery is not None else 0}"
)
print(
    f"Major retailers: "
    f"{len(major) if major is not None else 0}"
)
print(
    f"Primary roads: "
    f"{len(roads) if roads is not None else 0}"
)


# ------------------------------------------------------------
# Candidate points
# ------------------------------------------------------------

projected = sites.to_crs(UTM)

sites["site_point"] = (
    projected.geometry
    .centroid
    .to_crs(WGS84)
)

points = gpd.GeoDataFrame(
    sites.drop(
        columns="geometry",
        errors="ignore"
    ),
    geometry=sites["site_point"],
    crs=WGS84
)


# ------------------------------------------------------------
# Buildability screening
# ------------------------------------------------------------

sites["Population"] = num(
    sites,
    "Population"
)

# Nearest-road distance: prefer a live spatial join against
# the roads file when it's available, but fall back to the
# dataset's own pre-computed "nearest_road_miles" property
# when the roads file is missing. Without this fallback,
# every site would get an infinite road distance and fail
# the road-access filter entirely.
if roads is not None and len(roads) > 0:
    sites["nearest_road_miles_map"] = nearest_miles(
        points,
        roads
    )
elif "nearest_road_miles" in sites.columns:
    print(
        "Roads file not found — using the pre-computed "
        "'nearest_road_miles' property already in the "
        "source data instead of a live spatial join."
    )
    sites["nearest_road_miles_map"] = num(
        sites,
        "nearest_road_miles",
        default=np.inf
    )
else:
    sites["nearest_road_miles_map"] = nearest_miles(
        points,
        roads
    )

# Water body detection.
#
# IMPORTANT: `sites` here holds POINT geometry (each row is
# a single candidate location), not tract polygons. A point
# has zero area, so computing "population density" as
# Population / geometry.area is meaningless for point data —
# it silently produces 0-area / NaN-density for every row,
# which would then fail the water-body screen for every
# single site and empty the entire map. Prefer whichever
# real per-site density figure the source data already
# provides; only fall back to an area-based calculation when
# the geometry is genuinely polygonal.

_is_point_geometry = set(
    sites.geometry.geom_type.dropna().unique()
).issubset({"Point", "MultiPoint"})

if "population_density" in sites.columns:
    sites["population_density_calc"] = num(
        sites,
        "population_density"
    )

elif "ALAND" in sites.columns:
    sites["area_sq_miles_calc"] = (
        pd.to_numeric(sites["ALAND"], errors="coerce") / 2589988.11
    )
    sites["population_density_calc"] = (
        sites["Population"] /
        sites["area_sq_miles_calc"].replace(0, pd.NA)
    )

elif not _is_point_geometry:
    projected_for_area = sites.to_crs(UTM)
    sites["area_sq_miles_calc"] = (
        projected_for_area.geometry.area / 2589988.11
    )
    sites["population_density_calc"] = (
        sites["Population"] /
        sites["area_sq_miles_calc"].replace(0, pd.NA)
    )

else:
    print(
        "WARNING: geometry is Point with no 'ALAND' or "
        "'population_density' column to fall back on, so "
        "the water-body screen cannot be computed. All "
        "sites will be treated as unscreened for water — "
        "check the source data."
    )
    sites["population_density_calc"] = np.inf

# Filter out water bodies (population density below a
# threshold, in people per square mile) and other
# buildability constraints.
#
# IMPORTANT: unlike the earlier version of this script,
# the fallbacks below never fully bypass the water-body
# screen. A location that fails the density check is a
# location in/near water and must never reappear on the
# map — "remove invalid markers" means removed from the
# dataset, permanently, not hidden until a fallback
# branch quietly lets them back in. If the threshold
# turns out to be too strict for the current dataset, we
# progressively relax the density threshold itself
# (still excluding near-zero-density water) rather than
# skipping the screen.

pre_water_filter = sites[
    (sites["Population"] > 0)
].copy()

DENSITY_THRESHOLDS = [100, 50, 25, 10]

water_body_removals = (
    pre_water_filter["population_density_calc"] < DENSITY_THRESHOLDS[0]
).sum()

eligible = pd.DataFrame()

for threshold in DENSITY_THRESHOLDS:

    candidate = pre_water_filter[
        pre_water_filter["population_density_calc"] >= threshold
    ].copy()

    if len(candidate) > 0:
        eligible = candidate

        if threshold != DENSITY_THRESHOLDS[0]:
            print(
                f"Density threshold {DENSITY_THRESHOLDS[0]} "
                f"removed all sites; relaxed to {threshold} "
                "people/sq mi (still excludes water)."
            )

        break

# Apply road distance filtering only if we still have sites
if len(eligible) > 0:
    road_filtered = eligible[
        (
            eligible["nearest_road_miles_map"]
            <= MAX_ROAD_MILES
        )
        &
        (
            eligible["nearest_road_miles_map"]
            >= MIN_ROAD_MILES
        )
    ].copy()

    # If road filtering removes too many sites, relax the
    # road-distance requirement only (never the water
    # screen already applied above).
    if len(road_filtered) < len(eligible) * 0.5:  # If more than 50% removed
        print("Road distance filtering too strict, using relaxed criteria")
        eligible = eligible[
            (eligible["nearest_road_miles_map"] <= MAX_ROAD_MILES * 2)  # More lenient
        ].copy()
    else:
        eligible = road_filtered

print(f"Eligible sites: {len(eligible)}")
print(
    f"Removed: "
    f"{len(sites) - len(eligible)}"
)
print(f"Removed as water bodies: {water_body_removals}")

if len(eligible) == 0:
    print(
        "WARNING: No eligible sites survive filtering even "
        "at the most relaxed density threshold. Check the "
        "source data rather than bypassing the water-body "
        "screen — an empty map is safer than one with "
        "invalid/water locations on it."
    )


# ------------------------------------------------------------
# Competitors within 1 mile
#
# The precise "within 1 mile of this exact point" counts
# require the raw grocery/major-retailer point files (a live
# spatial join). When those aren't available, fall back to
# the dataset's own tract-level "grocery_stores" and
# "major_retailers" columns as the best available proxy,
# clearly flagged as such rather than silently returning 0
# for every site.
# ------------------------------------------------------------

ep = gpd.GeoDataFrame(
    eligible.drop(
        columns="geometry",
        errors="ignore"
    ),
    geometry=eligible["site_point"],
    crs=WGS84
)

if grocery is not None and len(grocery) > 0:
    eligible["nearby_grocery_competitors"] = count_radius(
        ep,
        grocery,
        COMP_RADIUS
    )
elif "grocery_stores" in eligible.columns:
    print(
        "Grocery-store file not found — using the "
        "tract-level 'grocery_stores' column as a proxy "
        "for grocery stores within 1 mile."
    )
    eligible["nearby_grocery_competitors"] = (
        num(eligible, "grocery_stores").round().astype(int)
    )
else:
    eligible["nearby_grocery_competitors"] = 0

if major is not None and len(major) > 0:
    eligible["nearby_major_retailers"] = count_radius(
        ep,
        major,
        COMP_RADIUS
    )
elif "major_retailers" in eligible.columns:
    print(
        "Major-retailer file not found — using the "
        "tract-level 'major_retailers' column as a proxy "
        "for major retailers within 1 mile."
    )
    eligible["nearby_major_retailers"] = (
        num(eligible, "major_retailers").round().astype(int)
    )
else:
    eligible["nearby_major_retailers"] = 0

eligible["nearby_competitors"] = (
    eligible["nearby_grocery_competitors"]
    +
    eligible["nearby_major_retailers"]
)


# ------------------------------------------------------------
# Estimated daily foot traffic proxy
# ------------------------------------------------------------

population = num(
    eligible,
    "Population"
)

apartments = num(
    eligible,
    "apartment_count"
)

groceries = num(
    eligible,
    "grocery_stores"
)

retailers = num(
    eligible,
    "major_retailers"
)

roads_count = num(
    eligible,
    "major_road_segments"
)

road_access = np.clip(
    1
    -
    eligible["nearest_road_miles_map"]
    / MAX_ROAD_MILES,
    0,
    1
)

eligible["estimated_daily_foot_traffic"] = (
    population * 0.02
    +
    apartments * 0.20
    +
    groceries * 75
    +
    retailers * 125
    +
    roads_count * 8 * road_access
).round().astype(int)

eligible["estimated_daily_foot_traffic"] = (
    eligible["estimated_daily_foot_traffic"]
    .clip(lower=25)
)


# ------------------------------------------------------------
# Rank assignment
# ------------------------------------------------------------

eligible["site_selection_score"] = num(
    eligible,
    "site_selection_score"
)

eligible = (
    eligible
    .sort_values(
        "site_selection_score",
        ascending=False
    )
    .reset_index(drop=True)
)

# Every eligible location gets a rank and a marker.
# Do NOT truncate the eligible set here — truncating
# silently discards legitimate locations, breaks the
# A/B/C/D grade distribution (D never appears with a
# small dataset), and defeats the Limit slider, which
# is meant to control *display*, not the underlying
# dataset. Filtering happens client-side in the browser
# so the full ranked dataset must be shipped to the map.

eligible["map_rank_num"] = np.arange(
    1,
    len(eligible) + 1
)

n_sites = len(eligible)

# Ranking system:
# A = rank 1-5    (best)
# B = rank 6-15   (second best)
# C = rank 16-30  (third best)
# D = rank 31+    (remaining, colored on a
#                  yellow -> orange -> red
#                  gradient by relative rank)
a_cut = 5
b_cut = 15
c_cut = 30


def rank_for(n):
    if n <= a_cut:
        return "A"

    if n <= b_cut:
        return "B"

    if n <= c_cut:
        return "C"

    return "D"


eligible["map_rank"] = (
    eligible["map_rank_num"]
    .map(rank_for)
)


# ------------------------------------------------------------
# Rank colors
#
# A/B/C are fixed colors. D is a continuous gradient from
# yellow (best D, rank c_cut+1) to red (worst D, the last
# rank), computed dynamically from each site's relative
# position within the D group — never hand-assigned.
# ------------------------------------------------------------

RANK_COLORS = {
    "A": "#7B2CBF",  # purple
    "B": "#2563EB",  # blue
    "C": "#16A34A",  # green
}

D_GRADIENT_STOPS = [
    (0.0, (0xFB, 0xBF, 0x24)),  # yellow
    (0.5, (0xF9, 0x73, 0x16)),  # orange
    (1.0, (0xDC, 0x26, 0x26)),  # red
]


def d_gradient_color(rank_num, d_start, d_end):
    """
    Interpolate a hex color along yellow -> orange -> red
    based on how far into the D group (ranks d_start..d_end)
    this rank_num falls. Higher-ranked (better) D sites are
    closer to yellow; the worst sites are closer to red.
    """

    if d_end <= d_start:
        t = 0.0
    else:
        t = (rank_num - d_start) / (d_end - d_start)

    t = min(1.0, max(0.0, t))

    for (t0, c0), (t1, c1) in zip(
        D_GRADIENT_STOPS,
        D_GRADIENT_STOPS[1:]
    ):
        if t0 <= t <= t1:
            local_t = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)

            r = round(c0[0] + (c1[0] - c0[0]) * local_t)
            g = round(c0[1] + (c1[1] - c0[1]) * local_t)
            b = round(c0[2] + (c1[2] - c0[2]) * local_t)

            return f"#{r:02X}{g:02X}{b:02X}"

    return "#DC2626"


# ------------------------------------------------------------
# Rescaled site location score
#
# Preserve the original score but expose a meaningful
# 1-10 score to the user.
# ------------------------------------------------------------

eligible["raw_site_selection_score"] = (
    eligible["site_selection_score"]
)

score_min = float(
    eligible["raw_site_selection_score"].min()
)

score_max = float(
    eligible["raw_site_selection_score"].max()
)

if score_max == score_min:

    eligible["site_location_score"] = 5.5

else:

    eligible["site_location_score"] = (
        1.0
        +
        9.0
        *
        (
            (
                eligible["raw_site_selection_score"]
                - score_min
            )
            /
            (
                score_max
                - score_min
            )
        )
    )

eligible["site_location_score"] = (
    eligible["site_location_score"]
    .clip(1.0, 10.0)
)


def rank_color(row):
    if row["map_rank"] == "D":
        return d_gradient_color(
            row["map_rank_num"],
            c_cut + 1,
            n_sites
        )

    return RANK_COLORS.get(
        row["map_rank"],
        "#6B7280"
    )


eligible["map_color"] = (
    eligible.apply(
        rank_color,
        axis=1
    )
)


# ------------------------------------------------------------
# Actual filter bounds
# ------------------------------------------------------------

# Handle potential NaN values in filter calculations
def safe_int(series):
    min_val = series.min()
    if pd.isna(min_val):
        return 0
    return int(min_val)

def safe_float(series):
    min_val = series.min()
    if pd.isna(min_val):
        return 0.0
    return float(min_val)

pop_min = safe_int(eligible["Population"])
pop_max = int(eligible["Population"].max())

income_series = num(
    eligible,
    "median_income"
)

income_min = safe_int(income_series)
income_max = int(income_series.max())

comp_min = safe_int(eligible["nearby_competitors"])
comp_max = int(eligible["nearby_competitors"].max())

major_min = safe_int(eligible["nearby_major_retailers"])
major_max = int(eligible["nearby_major_retailers"].max())

traffic_min = safe_int(eligible["estimated_daily_foot_traffic"])
traffic_max = int(eligible["estimated_daily_foot_traffic"].max())

score_min = safe_float(eligible["site_location_score"])
score_max = float(eligible["site_location_score"].max())

pop_step = max(
    1,
    int(
        round(
            (pop_max - pop_min) / 100
        )
    )
)

income_step = max(
    1,
    int(
        round(
            (income_max - income_min) / 100
        )
    )
)

# The Limit slider always spans 1..n_sites so every
# eligible location is reachable, but it starts at a
# sensible default so the map isn't overwhelming on
# first load.
limit_max = n_sites
limit_default = min(MAX_MARKERS_DEFAULT, n_sites)


# ------------------------------------------------------------
# Map
# ------------------------------------------------------------

center = (
    eligible["site_point"]
    .union_all()
    .centroid
)

m = folium.Map(
    location=[
        center.y,
        center.x
    ],
    zoom_start=10,
    tiles="OpenStreetMap",
    attr='© OpenStreetMap contributors',
    control_scale=True
)

map_name = m.get_name()


# ------------------------------------------------------------
# Map title
# ------------------------------------------------------------

m.get_root().html.add_child(
    Element("""
<div style="
position:fixed;
top:15px;
left:50%;
transform:translateX(-50%);
z-index:9999;
background:white;
padding:10px 22px;
border-radius:10px;
box-shadow:0 2px 12px rgba(0,0,0,.2);
font:700 20px Arial;">
Orlando Retail Site Selection
</div>
""")
)


# ------------------------------------------------------------
# Filters
# ------------------------------------------------------------

filters_html = f"""
<div id="filters" style="
position:fixed;
top:70px;
left:15px;
z-index:9999;
width:285px;
background:white;
padding:15px;
border-radius:12px;
box-shadow:0 3px 15px rgba(0,0,0,.22);
font:13px Arial;">

<div style="
font-size:17px;
font-weight:700;
margin-bottom:10px;">
Filters
</div>

<label>Rank</label>

<select
    id="rankFilter"
    style="
    width:100%;
    padding:6px;
    margin:4px 0 10px;">
    
<option value="ALL">All ranks</option>
<option value="A">A — Best</option>
<option value="B">B — Second best</option>
<option value="C">C — Third best</option>
<option value="D">D — Remaining</option>

</select>


<label>
Minimum Population:
<span id="popVal">
{pop_min:,}
</span>
</label>

<input
    id="popFilter"
    type="range"
    min="{pop_min}"
    max="{pop_max}"
    step="{pop_step}"
    value="{pop_min}"
    style="width:100%;">

<div class="range-row">
<span>{pop_min:,}</span>
<span>{pop_max:,}</span>
</div>


<label>
Minimum Median Income:
<span id="incomeVal">
${income_min:,}
</span>
</label>

<input
    id="incomeFilter"
    type="range"
    min="{income_min}"
    max="{income_max}"
    step="{income_step}"
    value="{income_min}"
    style="width:100%;">

<div class="range-row">
<span>${income_min:,}</span>
<span>${income_max:,}</span>
</div>


<label>
Maximum Competitors:
<span id="compVal">
{comp_max}
</span>
</label>

<input
    id="compFilter"
    type="range"
    min="{comp_min}"
    max="{comp_max}"
    step="1"
    value="{comp_max}"
    style="width:100%;">

<div class="range-row">
<span>{comp_min}</span>
<span>{comp_max}</span>
</div>


<label>
Maximum Major Retailers:
<span id="majorVal">
{major_max}
</span>
</label>

<input
    id="majorFilter"
    type="range"
    min="{major_min}"
    max="{major_max}"
    step="1"
    value="{major_max}"
    style="width:100%;">

<div class="range-row">
<span>{major_min}</span>
<span>{major_max}</span>
</div>


<label>
Minimum Site Location Score:
<span id="scoreVal">
{score_min:.1f}
</span>
</label>

<input
    id="scoreFilter"
    type="range"
    min="{score_min:.1f}"
    max="{score_max:.1f}"
    step="0.1"
    value="{score_min:.1f}"
    style="width:100%;">

<div class="range-row">
<span>{score_min:.1f}</span>
<span>{score_max:.1f}</span>
</div>


<label>
Minimum Daily Foot Traffic:
<span id="trafficVal">
{traffic_min:,}
</span>
</label>

<input
    id="trafficFilter"
    type="range"
    min="{traffic_min}"
    max="{traffic_max}"
    step="1"
    value="{traffic_min}"
    style="width:100%;">

<div class="range-row">
<span>{traffic_min:,}</span>
<span>{traffic_max:,}</span>
</div>


<label>
Limit:
<span id="limitVal">
{limit_default}
</span>
locations
</label>

<input
    id="limitFilter"
    type="range"
    min="1"
    max="{limit_max}"
    step="1"
    value="{limit_default}"
    style="width:100%;">

<div class="range-row">
<span>1</span>
<span>{limit_max}</span>
</div>


<button
    id="applyFilters"
    style="
    width:100%;
    margin-top:12px;
    padding:8px;
    border:0;
    border-radius:7px;
    background:#7B2CBF;
    color:white;
    cursor:pointer;
    font-weight:700;">
Apply Filters
</button>


<button
    id="resetFilters"
    style="
    width:100%;
    margin-top:7px;
    padding:8px;
    border:0;
    border-radius:7px;
    background:#222;
    color:white;
    cursor:pointer;">
Reset Filters
</button>


<div
    id="resultCount"
    style="
    margin-top:10px;
    font-weight:700;">
</div>

</div>
"""

m.get_root().html.add_child(
    Element(filters_html)
)


# ------------------------------------------------------------
# Filter styling
# ------------------------------------------------------------

m.get_root().html.add_child(
    Element("""
<style>

.range-row {
    display:flex;
    justify-content:space-between;
    color:#777;
    font-size:10px;
    margin-top:-2px;
    margin-bottom:10px;
}

#filters label {
    font-weight:600;
    display:block;
    margin-top:5px;
}

#filters input[type=range] {
    accent-color:#7B2CBF;
}

.rank-legend-btn {
    display:block;
    width:100%;
    text-align:left;
    border:0;
    background:white;
    padding:5px 4px;
    border-radius:6px;
    cursor:pointer;
    font:13px Arial;
}

.rank-legend-btn:hover {
    background:#f3f4f6;
}

</style>
""")
)


# ------------------------------------------------------------
# Legend
# ------------------------------------------------------------

m.get_root().html.add_child(
    Element(
        f"""
<div id="legend" style="
position:fixed;
bottom:25px;
right:20px;
z-index:9999;
background:white;
padding:14px;
border-radius:10px;
box-shadow:0 2px 10px rgba(0,0,0,.2);
font:13px Arial;
width:245px;">

<div style="
font-weight:700;
margin-bottom:8px;">
Site Selection Legend
</div>

<div style="
font-size:10px;
color:#666;
margin-bottom:6px;">
Click a rank to filter the map
</div>


<button
    class="rank-legend-btn"
    data-rank="A">

<span style="
color:#7B2CBF;
font-size:18px;">
●
</span>

A — Best (rank 1–5)

</button>


<button
    class="rank-legend-btn"
    data-rank="B">

<span style="
color:#2563EB;
font-size:18px;">
●
</span>

B — Second best (rank 6–15)

</button>


<button
    class="rank-legend-btn"
    data-rank="C">

<span style="
color:#16A34A;
font-size:18px;">
●
</span>

C — Third best (rank 16–30)

</button>


<button
    class="rank-legend-btn"
    data-rank="D"
    style="display:flex;align-items:center;gap:6px;">

<span style="
display:inline-block;
width:14px;
height:14px;
border-radius:50%;
background:linear-gradient(135deg,#FBBF24,#F97316,#DC2626);
flex-shrink:0;">
</span>

D — Remaining (rank 31+, yellow→red by rank)

</button>


<button
    class="rank-legend-btn"
    data-rank="ALL">

<span style="
color:#555;
font-size:18px;">
●
</span>

All ranks

</button>


<div style="
margin-top:9px;
padding-top:9px;
border-top:1px solid #eee;">

<div style="
font-weight:700;
margin-bottom:5px;">
Site Location Score
</div>

<div style="
height:10px;
border-radius:5px;
background:
linear-gradient(
to right,
#DC2626,
#F97316,
#FBBF24,
#16A34A,
#7B2CBF
);
">
</div>

<div style="
display:flex;
justify-content:space-between;
font-size:10px;
color:#666;
margin-top:3px;">

<span>1.0</span>
<span>10.0</span>

</div>

<div style="
font-size:10px;
color:#666;
margin-top:3px;">

Higher score = stronger site opportunity

</div>

</div>


<div style="
margin-top:9px;
padding-top:9px;
border-top:1px solid #eee;">

<div style="
font-weight:700;
margin-bottom:5px;">
Daily Foot Traffic
</div>

<div style="
height:10px;
border-radius:5px;
background:
linear-gradient(
to right,
#E5E7EB,
#2563EB
);
">
</div>

<div style="
display:flex;
justify-content:space-between;
font-size:10px;
color:#666;
margin-top:3px;">

<span>{traffic_min:,}</span>
<span>{traffic_max:,}</span>

</div>

<div style="
font-size:10px;
color:#666;
margin-top:3px;">

Estimated daily foot traffic proxy

</div>

</div>

</div>
"""
    )
)


# ------------------------------------------------------------
# Census tract outlines (optional context layer)
#
# IMPORTANT: this layer is only meaningful when `sites`
# holds polygon boundaries. If the source geometry is
# actually points (candidate site locations rather than
# tract polygons), adding it as a GeoJson layer with no
# pointToLayer style causes Leaflet to fall back to its
# DEFAULT blue pin marker for every single row — including
# invalid/water locations that were never meant to be
# shown. That silently reproduces the exact "hundreds of
# unfiltered blue markers" bug this map was fixed for, so
# we only draw this layer when the geometry is genuinely
# polygonal, and skip it otherwise.
# ------------------------------------------------------------

_site_geom_types = set(sites.geometry.geom_type.dropna().unique())

if _site_geom_types and _site_geom_types.issubset(
    {"Polygon", "MultiPolygon"}
):

    tracts_for_map = sites[
        [
            "GEOID",
            "geometry"
        ]
    ].copy()

    folium.GeoJson(
        tracts_for_map.to_json(),
        name="Census Tracts",
        style_function=lambda x: {
            "fillColor": "#ffffff",
            "fillOpacity": 0.01,
            "color": "#9ca3af",
            "weight": 0.5,
            "opacity": 0.3,
        },
    ).add_to(m)

else:
    print(
        "Skipping tract-outline context layer: "
        "site geometry is "
        f"{_site_geom_types or 'empty'}, not "
        "Polygon/MultiPolygon. Drawing it would "
        "render every raw location as a default, "
        "unfiltered marker (including invalid ones) "
        "instead of the ranked 'eligible' markers below."
    )


# ------------------------------------------------------------
# Ranked location markers + site data
# ------------------------------------------------------------

marker_data = []

for idx, r in eligible.iterrows():

    p = r["site_point"]

    rank = r["map_rank"]

    marker_color = r["map_color"]

    income = float(
        num(
            pd.DataFrame([r]),
            "median_income"
        ).iloc[0]
    )


    # Every site gets a ranked letter marker, drawn as a
    # classic map "pin" (teardrop) instead of a plain
    # circle: a soft color-matched glow, a rounded-top /
    # pointed-bottom pin body, a white letter badge, and
    # the rank letter colored to match the pin.

    icon_html = f"""
<div style="width:40px;height:54px;pointer-events:auto;cursor:pointer;">
<svg width="40" height="54" viewBox="0 0 40 54" xmlns="http://www.w3.org/2000/svg" style="filter:drop-shadow(0 3px 4px rgba(0,0,0,.35));">
<path d="M20,3 C10.6,3 3,10.6 3,20 C3,33 20,51 20,51 C20,51 37,33 37,20 C37,10.6 29.4,3 20,3 Z" fill="{marker_color}" stroke="white" stroke-width="2"/>
<text x="20" y="24" text-anchor="middle" font-family="Arial, sans-serif" font-weight="800" font-size="15" fill="white">{rank}</text>
</svg>
</div>
"""

    marker = folium.Marker(
        location=[
            p.y,
            p.x
        ],

        icon=folium.DivIcon(
            html=icon_html,
            icon_size=(40, 54),
            icon_anchor=(20, 51),
        ),

        tooltip=(
            f"{rank} Rank • "
            f"Site Location Score "
            f"{r['site_location_score']:.1f}/10 • "
            f"Click for details"
        ),
    )

    marker.add_to(m)


    marker_data.append({
        "js": marker.get_name(),

        "rank": rank,

        "rank_num": int(
            r["map_rank_num"]
        ),

        "geoid": str(
            r["GEOID"]
        ),

        "population": int(
            r["Population"]
        ),

        "income": income,

        "competitors": int(
            r["nearby_competitors"]
        ),

        "major": int(
            r["nearby_major_retailers"]
        ),

        "groceries": int(
            r["nearby_grocery_competitors"]
        ),

        "traffic": int(
            r["estimated_daily_foot_traffic"]
        ),

        "score": float(
            r["site_location_score"]
        ),

        "raw_score": float(
            r["raw_site_selection_score"]
        ),

        "road": float(
            r["nearest_road_miles_map"]
        ),

        "lat": float(p.y),

        "lon": float(p.x),
    })


# ------------------------------------------------------------
# Information cards + filtering JavaScript
# ------------------------------------------------------------

js = f"""
<script>

var SITE_DATA = {json.dumps(marker_data)};

function getMap() {{
    return window["{map_name}"];
}}

var CARD = null;


function money(x) {{
    return Number(x).toLocaleString(
        'en-US',
        {{
            style:'currency',
            currency:'USD',
            maximumFractionDigits:0
        }}
    );
}}


function fmt(x) {{
    return Number(x).toLocaleString(
        'en-US'
    );
}}


function showCard(s) {{

    if (CARD) {{
        CARD.remove();
    }}


    var colors = {{
        A:'#7B2CBF',
        B:'#2563EB',
        C:'#16A34A',
        D:'#F97316'
    }};


    var card =
        document.createElement('div');


    card.style.cssText =
        'position:fixed;' +
        'top:50%;' +
        'left:50%;' +
        'transform:translate(-50%,-50%);' +
        'width:370px;' +
        'max-width:calc(100vw - 40px);' +
        'max-height:90vh;' +
        'overflow:auto;' +
        'background:white;' +
        'z-index:10001;' +
        'padding:20px;' +
        'border-radius:16px;' +
        'box-shadow:0 8px 35px rgba(0,0,0,.30);' +
        'font-family:Arial;';


    card.innerHTML = `

      <div style="
      display:flex;
      justify-content:space-between;
      align-items:center;">

        <div>

          <div style="
          font-size:11px;
          color:#777;">
          SITE RANK
          </div>

          <div style="
          font-size:40px;
          font-weight:800;
          color:${{colors[s.rank]}};">

          ${{s.rank}}

          </div>

        </div>


        <button
            id="closeCard"
            style="
            border:0;
            background:#f3f4f6;
            width:34px;
            height:34px;
            border-radius:50%;
            font-size:20px;
            cursor:pointer;">

            ×

        </button>

      </div>


      <div style="
      color:#666;
      font-size:13px;
      margin-bottom:12px;">

      Census Tract
      ${{s.geoid}}
      • Rank #${{s.rank_num}}

      </div>


      <div style="
      background:#f8f5ff;
      padding:12px;
      border-radius:12px;">

        <div style="
        font-size:11px;
        color:#666;">

        SITE LOCATION SCORE

        </div>

        <div style="
        font-size:28px;
        font-weight:800;">

        ${{s.score.toFixed(1)}}/10

        </div>

        <div style="
        font-size:10px;
        color:#777;
        margin-top:3px;">

        Rescaled relative to all eligible locations

        </div>

      </div>


      <div style="
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:9px;
      margin-top:12px;">

        <div class="stat">
            <small>POPULATION</small>
            <b>${{fmt(s.population)}}</b>
        </div>

        <div class="stat">
            <small>MEDIAN INCOME</small>
            <b>${{money(s.income)}}</b>
        </div>

        <div class="stat">
            <small>COMPETITORS ≤ 1 MI</small>
            <b>${{fmt(s.competitors)}}</b>
        </div>

        <div class="stat">
            <small>MAJOR RETAILERS ≤ 1 MI</small>
            <b>${{fmt(s.major)}}</b>
        </div>

        <div class="stat">
            <small>GROCERY STORES ≤ 1 MI</small>
            <b>${{fmt(s.groceries)}}</b>
        </div>

        <div class="stat">
            <small>NEAREST ROAD</small>
            <b>${{s.road.toFixed(2)}} mi</b>
        </div>

      </div>


      <div style="
      margin-top:14px;
      background:#eef6ff;
      padding:14px;
      border-radius:12px;">

        <div style="
        font-size:11px;
        color:#555;">

        ESTIMATED DAILY FOOT TRAFFIC

        </div>

        <div style="
        font-size:29px;
        font-weight:800;
        color:#2563EB;">

        ${{fmt(s.traffic)}}

        </div>

        <div style="
        font-size:10px;
        color:#666;
        margin-top:5px;">

        Model-based proxy using population,
        housing, nearby retail destinations
        and road accessibility. This is not
        an observed pedestrian count.

        </div>

      </div>

    `;


    // Used to determine whether the card's
    // location has been filtered out.

    card.dataset.geoid = s.geoid;


    document.body.appendChild(card);

    CARD = card;


    document.getElementById(
        'closeCard'
    ).onclick = function() {{

        card.remove();

        CARD = null;
    }};
}}


var style =
    document.createElement('style');


style.innerHTML =

    '.stat{{' +
    'background:#f7f7f7;' +
    'padding:10px;' +
    'border-radius:10px;' +
    '}}' +

    '.stat small{{' +
    'display:block;' +
    'color:#777;' +
    'font-size:9px;' +
    '}}' +

    '.stat b{{' +
    'display:block;' +
    'margin-top:3px;' +
    'font-size:14px;' +
    '}}';


document.head.appendChild(style);


function bindSiteMarkers() {{

    SITE_DATA.forEach(function(s) {{

        var marker = window[s.js];


        if (!marker) {{

            console.warn(
                'Missing marker for site:',
                s.geoid
            );

            return;
        }}


        // Add the click handler with proper event handling
        if (!marker._siteCardBound) {{

            marker.on(
                'click',
                function(e) {{
                    e.originalEvent.stopPropagation();
                    showCard(s);
                }}
            );

            marker._siteCardBound = true;
        }}

    }});
}}


function applyFilters() {{

    var rank =
        document.getElementById(
            'rankFilter'
        ).value;


    var minPop =
        Number(
            document.getElementById(
                'popFilter'
            ).value
        );


    var minIncome =
        Number(
            document.getElementById(
                'incomeFilter'
            ).value
        );


    var maxComp =
        Number(
            document.getElementById(
                'compFilter'
            ).value
        );


    var maxMajor =
        Number(
            document.getElementById(
                'majorFilter'
            ).value
        );


    var minScore =
        Number(
            document.getElementById(
                'scoreFilter'
            ).value
        );


    var minTraffic =
        Number(
            document.getElementById(
                'trafficFilter'
            ).value
        );

    var limit =
        Number(
            document.getElementById(
                'limitFilter'
            ).value
        );

    var shown = 0;


    // Step 1: find every site that satisfies the current
    // filter criteria (rank + all sliders). The Limit
    // slider is applied separately, AFTER filtering, so
    // it always operates on the filtered dataset rather
    // than the full dataset.

    var matching = SITE_DATA.filter(function(s) {{

        var marker =
            window[s.js];

        if (!marker) {{

            console.warn(
                'Missing marker for site:',
                s.geoid
            );

            return false;
        }}

        return (

            (
                rank === 'ALL'
                ||
                s.rank === rank
            )

            &&

            s.population >= minPop

            &&

            s.income >= minIncome

            &&

            s.competitors <= maxComp

            &&

            s.major <= maxMajor

            &&

            s.score >= minScore

            &&

            s.traffic >= minTraffic
        );
    }});


    // Step 2: rank the filtered locations (#1 = highest
    // priority) and keep only the top N, where N is the
    // selected Limit. If the limit exceeds the number of
    // filtered locations, every filtered location is shown.

    matching.sort(function(a, b) {{
        return a.rank_num - b.rank_num;
    }});

    var toShow = matching.slice(0, limit);

    var visibleGeoids = {{}};

    toShow.forEach(function(s) {{
        visibleGeoids[s.geoid] = true;
    }});


    // Step 3: sync every marker's visibility on the map
    // with the computed visible set.

    SITE_DATA.forEach(function(s) {{

        var marker =
            window[s.js];

        if (!marker) {{
            return;
        }}

        if (visibleGeoids[s.geoid]) {{

            if (!getMap().hasLayer(marker)) {{

                marker.addTo(getMap());

            }}

            shown++;

        }} else {{

            if (getMap().hasLayer(marker)) {{

                getMap().removeLayer(marker);

            }}
        }}

    }});


    document.getElementById(
        'resultCount'
    ).innerText =
        shown +
        ' of ' +
        matching.length +
        ' matching locations shown';


    // Close the card if its location
    // has been filtered out.

    if (
        CARD
        &&
        CARD.dataset.geoid
    ) {{

        var current =
            SITE_DATA.find(
                function(s) {{

                    return (
                        s.geoid
                        ===
                        CARD.dataset.geoid
                    );

                }}
            );


        if (current) {{

            var currentMarker =
                window[current.js];


            if (
                currentMarker
                &&
                !getMap().hasLayer(
                    currentMarker
                )
            ) {{

                CARD.remove();

                CARD = null;

            }}

        }}

    }}

}}


function setRank(rank) {{

    document.getElementById(
        'rankFilter'
    ).value = rank;

    applyFilters();

}}


// Wait until Folium's generated
// marker variables exist before binding
// the click handlers.

function initializeSiteMarkers(
    attempt
) {{

    var allReady =
        SITE_DATA.every(
            function(s) {{
                return !!window[s.js];
            }}
        );


    if (!allReady) {{

        if (attempt < 60) {{

            setTimeout(
                function() {{
                    initializeSiteMarkers(
                        attempt + 1
                    );
                }},
                50
            );

        }}

        return;

    }}


    bindSiteMarkers();

    applyFilters();

}}


setTimeout(
    function() {{
        initializeSiteMarkers(0);
    }},
    0
);


// Apply button - add event listener properly
// Use a more reliable approach

document.addEventListener('DOMContentLoaded', function() {{
    // Apply button
    var applyBtn = document.getElementById('applyFilters');
    if (applyBtn) {{
        applyBtn.addEventListener('click', function() {{
            console.log('Apply button clicked');
            applyFilters();
        }});
    }}

    // Rank changes are staged until Apply is pressed.
    var rankFilter = document.getElementById('rankFilter');
    if (rankFilter) {{
        rankFilter.onchange = function() {{
            // Intentionally do not apply yet.
        }};
    }}

    // Sliders update their displayed values
    // but do not change the map until Apply.
    var popFilter = document.getElementById('popFilter');
    if (popFilter) {{
        popFilter.oninput = function() {{
            document.getElementById('popVal').innerText = fmt(this.value);
        }};
    }}

    var incomeFilter = document.getElementById('incomeFilter');
    if (incomeFilter) {{
        incomeFilter.oninput = function() {{
            document.getElementById('incomeVal').innerText = money(this.value);
        }};
    }}

    var compFilter = document.getElementById('compFilter');
    if (compFilter) {{
        compFilter.oninput = function() {{
            document.getElementById('compVal').innerText = this.value;
        }};
    }}

    var majorFilter = document.getElementById('majorFilter');
    if (majorFilter) {{
        majorFilter.oninput = function() {{
            document.getElementById('majorVal').innerText = this.value;
        }};
    }}

    var scoreFilter = document.getElementById('scoreFilter');
    if (scoreFilter) {{
        scoreFilter.oninput = function() {{
            document.getElementById('scoreVal').innerText = parseFloat(this.value).toFixed(1);
        }};
    }}

    var trafficFilter = document.getElementById('trafficFilter');
    if (trafficFilter) {{
        trafficFilter.oninput = function() {{
            document.getElementById('trafficVal').innerText = fmt(this.value);
        }};
    }}

    // The Limit slider updates its displayed value live,
    // but (like the other sliders) only takes effect on
    // the map once Apply Filters is pressed.
    var limitFilter = document.getElementById('limitFilter');
    if (limitFilter) {{
        limitFilter.oninput = function() {{
            document.getElementById('limitVal').innerText = this.value;
        }};
    }}

    // Pressing Enter applies the filters.
    var filtersDiv = document.getElementById('filters');
    if (filtersDiv) {{
        filtersDiv.addEventListener('keydown', function(event) {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                applyFilters();
            }}
        }});
    }}

    // Legend buttons remain immediate one-click rank filters.
    document.querySelectorAll('.rank-legend-btn').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            setRank(this.dataset.rank);
        }});
    }});

    // Reset filters
    var resetBtn = document.getElementById('resetFilters');
    if (resetBtn) {{
        resetBtn.onclick = function() {{
            document.getElementById('rankFilter').value = 'ALL';
            document.getElementById('popFilter').value = {pop_min};
            document.getElementById('incomeFilter').value = {income_min};
            document.getElementById('compFilter').value = {comp_max};
            document.getElementById('majorFilter').value = {major_max};
            document.getElementById('scoreFilter').value = {score_min:.1f};
            document.getElementById('trafficFilter').value = {traffic_min};
            document.getElementById('limitFilter').value = {limit_default};
            document.getElementById('popVal').innerText = fmt({pop_min});
            document.getElementById('incomeVal').innerText = money({income_min});
            document.getElementById('compVal').innerText = {comp_max};
            document.getElementById('majorVal').innerText = {major_max};
            document.getElementById('scoreVal').innerText = {score_min:.1f};
            document.getElementById('trafficVal').innerText = fmt({traffic_min});
            document.getElementById('limitVal').innerText = {limit_default};
            if (CARD) {{
                CARD.remove();
                CARD = null;
            }}
            applyFilters();
        }};
    }}
}});

</script>
"""

m.get_root().html.add_child(
    Element(js)
)


# ------------------------------------------------------------
# Methodology note
# ------------------------------------------------------------

m.get_root().html.add_child(
    Element("""
<div style="
position:fixed;
bottom:25px;
left:15px;
z-index:9998;
background:rgba(255,255,255,.95);
padding:10px 12px;
border-radius:8px;
box-shadow:0 2px 8px rgba(0,0,0,.15);
font:10px Arial;
max-width:340px;">

<b>Foot-traffic methodology:</b>

Estimated Daily Foot Traffic is a modeled
proxy, not a measured count.

It combines resident population,
apartment units, retail destinations
and road accessibility.

Direct pedestrian counts would be
required for observed foot traffic.

</div>
""")
)


# ------------------------------------------------------------
# Save HTML
# ------------------------------------------------------------

os.makedirs(
    os.path.dirname(OUTPUT),
    exist_ok=True
)

m.save(OUTPUT)


# ------------------------------------------------------------
# Completion information
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("MAP COMPLETE")
print("=" * 70)

print(
    f"Eligible locations: "
    f"{len(eligible)}"
)

print(
    f"Removed zero-pop / poor-access candidates: "
    f"{len(sites) - len(eligible)}"
)

print(
    f"A: "
    f"{(eligible.map_rank == 'A').sum()}"
)

print(
    f"B: "
    f"{(eligible.map_rank == 'B').sum()}"
)

print(
    f"C: "
    f"{(eligible.map_rank == 'C').sum()}"
)

print(
    f"D: "
    f"{(eligible.map_rank == 'D').sum()}"
)

print(
    f"Population filter range: "
    f"{pop_min:,} - {pop_max:,}"
)

print(
    f"Median income filter range: "
    f"${income_min:,} - ${income_max:,}"
)

print(
    f"Competitor filter range: "
    f"{comp_min} - {comp_max}"
)

print(
    f"Major retailer filter range: "
    f"{major_min} - {major_max}"
)

print(
    f"Daily foot traffic range: "
    f"{traffic_min:,} - {traffic_max:,}"
)

print(
    f"Site location score range: "
    f"{eligible['site_location_score'].min():.1f} "
    f"- "
    f"{eligible['site_location_score'].max():.1f}"
)

print(
    f"Saved: {OUTPUT}"
)
