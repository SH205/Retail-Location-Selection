# 🏪 Retail Site Selection - Orlando

## 📌 Project Overview

**Business Problem:** Where should a retail company open its next location in the Orlando market?

### Goal of Project
Identify and rank potential retail locations in the Orlando market using demographic, competitive, geographic, and accessibility data.

### Brief Description
This is an end-to-end **data engineering, analytics, and business intelligence project** that combines public Census and OpenStreetMap data to evaluate potential retail expansion sites.

The pipeline:
1. Collects public data from multiple sources
2. Cleans and validates the data
3. Performs geospatial analysis
4. Integrates demographic and competitive data
5. Engineers features for site evaluation
6. Calculates a Site Selection Score
7. Ranks potential locations
8. Produces SQL analytics and an interactive map

### Results of Project
- **267** census tracts analyzed
- **194** potential retail locations evaluated
- **20** highest-ranked locations identified
- Calculated **Site Selection Scores**
- Analyzed population, income, competition, and retail activity
- Estimated daily foot traffic
- Built an interactive HTML map

## 🗺️ Interactive Map

The final output is an interactive HTML map that allows users to explore and compare potential retail locations.

**[Open Interactive Map](https://sh205.github.io/Retail-Location-Selection/orlando_site_selection_map.html)**


### Skills Used
**Data Engineering • ETL • Data Cleaning • Data Validation • Data Integration • SQL Analytics • Statistical Analysis • Feature Engineering • Geospatial Analysis • Site Scoring & Ranking • Data Visualization • Business Intelligence**

### Tech Used
**Python • SQL • HTML • CSS • JavaScript • Pandas • GeoPandas • Leaflet.js • Git • GitHub • Databricks**

---

## 📊 Data Sources

| Source | Data Used | Purpose |
|---|---|---|
| **U.S. Census ACS 2024 5-Year** | Population, income, poverty, housing | Market demand |
| **OpenStreetMap** | Grocery & supermarket locations | Competition |
| **OpenStreetMap** | Major retailers | Commercial activity |
| **OpenStreetMap** | Road network | Accessibility |
| **OpenStreetMap** | Water features | Geographic constraints |
| **Derived / Modelled** | Foot traffic proxy | Customer activity |

---

## 📈 Dashboard

### KPI Summary
<img width="1188" height="382" alt="Screenshot 2026-09-02 at 3 42 04 PM" src="https://github.com/user-attachments/assets/360ef196-791c-4add-aac4-a6624e04b5b1" />


### Market Analysis
<img width="1188" height="429" alt="Screenshot 2026-09-01 at 5 18 42 PM" src="https://github.com/user-attachments/assets/74714983-7a8e-458e-9b52-a07d24403517" />

---

## 📁 Project Structure

```text
orlando-retail-location-selection/
│
├── README.md
├── requirements.txt
│
├── data/
│   ├── raw/
│   │   ├── osm/
│   │   │   └── businesses/
│   │   └── census/
│   │
│   └── processed/
│    ├── ...
│
├── src/
│   ├── create_orlando_map.py
│   └── ...
│
└── docs/
    └── orlando_site_selection_map.html
