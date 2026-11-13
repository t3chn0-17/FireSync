# Kiddy Spiders

**Transparent, reproducible harmonization of MODIS and VIIRS active-fire detections.**

NASA Space Apps Challenge 2026 | Challenge: *Harmonization of MODIS and VIIRS Hot Spots*

> **Status notice:** This README describes the project's goals, intended methodology, and a proposed structure. Items are labeled **Implemented**, **In progress**, or **Planned** in the [Project Status](#21-project-status) section. No experimental results, accuracy metrics, or performance figures are reported here, because none have been produced yet. Replace the placeholders marked `TODO` as the implementation matures.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Proposed Solution](#3-proposed-solution)
4. [Project Objectives](#4-project-objectives)
5. [Key Features](#5-key-features)
6. [Scientific Methodology](#6-scientific-methodology)
7. [MODIS vs VIIRS Comparison](#7-modis-vs-viirs-comparison)
8. [Data Sources and Attribution](#8-data-sources-and-attribution)
9. [Technology Stack](#9-technology-stack)
10. [System Architecture](#10-system-architecture)
11. [Repository Structure](#11-repository-structure)
12. [Installation and Setup](#12-installation-and-setup)
13. [Environment Variables](#13-environment-variables)
14. [API Documentation](#14-api-documentation)
15. [Data Processing Workflow](#15-data-processing-workflow)
16. [Validation Methodology](#16-validation-methodology)
17. [Known Limitations](#17-known-limitations)
18. [Team](#18-team)
19. [Acknowledgements](#19-acknowledgements)
20. [License](#20-license)
21. [Project Status](#21-project-status)

---

## 1. Project Overview

Kiddy Spiders is a software project developed for the NASA Space Apps Challenge 2026. It explores how active-fire observations from two NASA satellite instruments, **MODIS** (Moderate Resolution Imaging Spectroradiometer) and **VIIRS** (Visible Infrared Imaging Radiometer Suite), can be compared and harmonized.

The two instruments have produced thermal-anomaly detections for years, and both are distributed through NASA FIRMS (Fire Information for Resource Management System). Because they differ in spatial resolution, overpass timing, and detection algorithms, their records cannot be merged by simple concatenation. This project investigates methods for aligning them in space and time, comparing them statistically, and presenting the result in an interactive interface while keeping every record traceable to its source sensor.

## 2. Problem Statement

Active-fire records from MODIS and VIIRS describe overlapping phenomena but are not directly interchangeable:

- Each detection represents a **pixel**, not a fire. A single fire may produce many detections, and the same fire may be seen by several sensors or overpasses.
- Pixel footprints differ between instruments and vary with scan angle.
- Overpass times differ, so the sensors observe fires at different stages of their diurnal cycle.
- Fire Radiative Power (FRP) is derived with sensor-specific algorithms and sensitivities, so values are not guaranteed to be directly comparable.
- Near-real-time and standard (reprocessed) products can differ in quality and availability.

Without careful harmonization, combining the two records risks double counting, misleading trends, and false conclusions about changes in fire activity.

## 3. Proposed Solution

Kiddy Spiders proposes a pipeline and web interface that:

1. Ingests MODIS and VIIRS active-fire data from NASA FIRMS.
2. Normalizes the schemas while **preserving sensor, satellite, product, and processing-type provenance** on every record.
3. Applies explicit, documented spatial and temporal matching rules to identify co-observed detections.
4. Computes statistical comparisons of detection agreement and FRP.
5. Surfaces historical activity and statistical anomalies through interactive visualizations.
6. Logs parameters and experiments so that every result can be reproduced.

## 4. Project Objectives

- Define a transparent method for spatial and temporal harmonization of MODIS and VIIRS detections.
- Quantify sensor agreement and differences, including FRP, using documented statistical methods.
- Support exploration of historical fire activity across regions and time ranges.
- Flag statistical anomalies in fire activity relative to a historical baseline, for retrospective exploration.
- Make methodology, parameters, and limitations explicit and reproducible.

## 5. Key Features

Feature status is tracked in [Project Status](#21-project-status). The list below describes intended capabilities.

- **Provenance-preserving ingestion:** every record retains its instrument, satellite, product, and NRT or standard flag.
- **Spatial harmonization:** configurable matching between detections of different footprints.
- **Temporal harmonization:** configurable time-window matching that accounts for different overpass times.
- **Statistical comparison:** agreement and difference metrics between sensors.
- **FRP analysis:** distribution comparison and relationship analysis between sensor FRP values.
- **Historical activity analysis:** aggregated views by region and time period.
- **Anomaly detection:** retrospective identification of unusual activity relative to a historical baseline.
- **Interactive visualization:** map and chart views for exploring results.
- **Experiment logging:** recorded parameters and outputs for reproducibility.

## 6. Scientific Methodology

The methodology below is the intended approach. Specific thresholds and parameters are to be chosen and documented during implementation, and should be justified by the data rather than assumed.

### 6.1 Principles

- **Detections are not fires.** Raw detection counts must never be reported as unique fire counts. Any count of "fire events" requires an explicit, documented clustering definition.
- **Provenance is preserved.** Harmonized outputs always reference the original source records.
- **NRT and standard products are kept distinct.** Near-real-time data may be superseded by science-quality reprocessed data. They are labeled and not silently mixed.
- **Differences are reported, not hidden.** Where sensors disagree, the disagreement is a result, not an error to be smoothed away.

### 6.2 Spatial Harmonization

- Represent each detection with its location and, where available, its pixel dimensions (scan and track).
- Match detections across sensors using a distance criterion informed by the pixel footprints of the two instruments.
- Handle one-to-many and many-to-one matches explicitly rather than forcing one-to-one pairing.
- Optionally aggregate to a common grid for regional comparison, with the grid size documented.

### 6.3 Temporal Harmonization

- Use the detection acquisition date and time as the temporal reference.
- Apply a configurable time window for candidate matches, chosen with the overpass characteristics of each satellite in mind.
- Report results at multiple temporal aggregations (for example, per overpass, daily, monthly) rather than assuming one is correct.

### 6.4 FRP Analysis

- Compare FRP distributions between sensors, overall and by region or land-cover context where available.
- Analyze FRP for matched detections separately from unmatched detections.
- Treat FRP as sensor-derived estimates with associated uncertainty, not as ground truth.

### 6.5 Anomaly Detection

Anomaly detection in this project is **retrospective and descriptive**. It identifies periods or regions where observed activity deviates from a historical baseline. It does **not** predict future fires and must not be interpreted as a forecast.

## 7. MODIS vs VIIRS Comparison

MODIS and VIIRS are **not identical** in characteristics. The table summarizes general differences relevant to harmonization. Values are approximate and should be verified against current NASA documentation before being relied upon.

| Aspect | MODIS | VIIRS |
|---|---|---|
| Platforms | Terra and Aqua | Suomi NPP, NOAA-20, NOAA-21 |
| Nominal active-fire spatial resolution | About 1 km at nadir | About 375 m at nadir (I-band product) |
| Pixel size variation | Grows with scan angle | Grows with scan angle, with less distortion toward the swath edge than MODIS |
| Detection algorithm | MODIS active-fire algorithm | VIIRS active-fire algorithm, separate from MODIS |
| Confidence field | Numeric percentage | Categorical (low, nominal, high) |
| Sensitivity to small or low-intensity fires | Lower | Generally higher, owing to finer resolution |
| Overpass timing | Differs by satellite | Differs by satellite and from MODIS |
| Record length | Longer historical record | Shorter historical record |

Practical consequences for harmonization:

- A single VIIRS detection may fall inside a single MODIS pixel, and several VIIRS detections may correspond to one MODIS detection.
- Confidence values are on different scales and are not directly comparable.
- Differences in overpass time mean that agreement between sensors is not expected to be perfect even for the same fire.

## 8. Data Sources and Attribution

**Primary source:** NASA FIRMS (Fire Information for Resource Management System), which distributes MODIS and VIIRS active-fire data.

- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/
- FIRMS API information: https://firms.modaps.eosdis.nasa.gov/api/

Product types the project may use:

| Product type | Description | Handling in this project |
|---|---|---|
| Near real time (NRT) | Available shortly after observation, subject to later revision | Labeled as NRT; kept separate from standard data |
| Standard (science quality) | Reprocessed, intended for scientific analysis | Labeled as standard; preferred for historical analysis |

**Attribution:** Fire data are provided by NASA FIRMS, operated by NASA's Land, Atmosphere Near real-time Capability for EOS (LANCE) and Earth Science Data and Information System (ESDIS). Users should follow the current NASA FIRMS data citation and use guidelines. This project does not claim ownership of NASA datasets.

> `TODO`: Add the exact FIRMS citation text and the specific product names and collection versions actually used, once finalized.

## 9. Technology Stack

The stack below reflects the intended roles of the team. **Confirm each item against the actual codebase and remove anything not used.**

| Layer | Technology | Status |
|---|---|---|
| Backend and data processing | Python | `TODO` confirm |
| Data handling | Python scientific libraries (for example, pandas, NumPy) | `TODO` confirm |
| Frontend | React | `TODO` confirm |
| Visualization | Map and chart libraries | `TODO` choose and document |
| Data source | NASA FIRMS | Planned |

## 10. System Architecture

The following diagram shows the proposed high-level data flow. It is a design intent, not a statement of what is implemented.

```text
+------------------+     +----------------------+     +-------------------------+
|   NASA FIRMS     | --> |  Ingestion Layer     | --> |  Normalization          |
|  MODIS and VIIRS |     |  (fetch, cache)      |     |  (schema + provenance)  |
+------------------+     +----------------------+     +-------------------------+
                                                                  |
                                                                  v
+------------------+     +----------------------+     +-------------------------+
|   Web Frontend   | <-- |  Backend Service     | <-- |  Harmonization and      |
|  (React)         |     |  (Python)            |     |  Analysis               |
+------------------+     +----------------------+     |  spatial, temporal,     |
                                                      |  FRP, anomaly           |
                                                      +-------------------------+
```

Design considerations:

- Raw data and harmonized data are stored separately so original records are never overwritten.
- Each analysis run records its parameters for reproducibility.

## 11. Repository Structure

> **Suggested structure, not verified.** This tree is a proposal. Replace it with the actual layout once the repository is organized.

```text
kiddy-spiders/
├── README.md
├── LICENSE
├── backend/            # Python: ingestion, harmonization, analysis
├── frontend/           # React: UI and visualization
├── data/
│   ├── raw/            # Unmodified downloads from FIRMS (not committed)
│   └── processed/      # Harmonized outputs (not committed)
├── notebooks/          # Exploratory analysis and experiment logs
├── docs/               # Methodology notes and research documentation
└── tests/              # Automated tests
```

## 12. Installation and Setup

> **Assumed instructions.** These steps are templates based on the intended stack. Adjust the commands and file names to match the actual repository before publishing.

### Prerequisites

- Git
- Python 3.10 or newer (version to be confirmed)
- Node.js and npm (version to be confirmed)
- A NASA FIRMS MAP_KEY (see [Environment Variables](#13-environment-variables))

### Clone the repository

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git
cd YOUR_REPO
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # TODO: confirm file exists
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # TODO: confirm script name
```

## 13. Environment Variables

Never commit secrets to the repository.

| Variable | Purpose | Required |
|---|---|---|
| `FIRMS_MAP_KEY` | NASA FIRMS API key, requested from the FIRMS website | Yes, if fetching from the FIRMS API |

> `TODO`: Add any further variables (for example, ports, cache paths) only if they exist in the implementation.

Example `.env` file, to be kept out of version control:

```bash
FIRMS_MAP_KEY=your_map_key_here
```

## 14. API Documentation

**Not documented.** This README does not list endpoints because no implemented API has been confirmed. Endpoint documentation will be added here only once the backend exposes endpoints that actually exist.

## 15. Data Processing Workflow

Intended workflow. Each stage is documented as it is implemented.

1. **Acquire:** request MODIS and VIIRS detections from FIRMS for a chosen region and date range.
2. **Label:** record sensor, satellite, product, and NRT or standard status on every record.
3. **Normalize:** map fields to a common schema without discarding sensor-specific fields (for example, native confidence values).
4. **Clean:** handle missing values and invalid records, logging what was removed and why.
5. **Spatially match:** identify candidate cross-sensor matches using documented distance rules.
6. **Temporally match:** restrict candidates by the configured time window.
7. **Compare:** compute agreement and FRP statistics for matched and unmatched detections.
8. **Analyze history and anomalies:** aggregate over time and compare against a baseline.
9. **Present:** serve results to the frontend with provenance visible.
10. **Log:** save parameters and outputs for each run.

## 16. Validation Methodology

Validation is planned but not yet performed. No accuracy figures are claimed.

- **Internal consistency checks:** verify that harmonization does not change or lose original records and that provenance is retained.
- **Sensitivity analysis:** evaluate how results change when matching distance and time-window parameters vary.
- **Reproducibility:** confirm that re-running with logged parameters yields the same output.
- **Comparison with documentation:** check derived behavior against published product documentation.
- **Independent reference data:** if suitable reference data (for example, fire perimeter records) are identified, use them for comparison, and state their own limitations.

## 17. Known Limitations

- Active-fire detections are not a direct measure of burned area or fire size.
- Pixel-level detections can include false alarms and can miss small, short-lived, or obscured fires (for example, under cloud or thick smoke).
- Differing spatial resolutions mean matching is inherently approximate.
- Differing overpass times mean sensors do not observe the same moment of a fire.
- FRP is sensor-derived and carries uncertainty; cross-sensor FRP comparisons are not assumed to be equivalent.
- NRT data may be revised in later standard processing.
- Anomaly detection is retrospective and does not forecast fires.
- Historical coverage differs between MODIS and VIIRS.
- Project status is early and the methodology is subject to change.

## 18. Team

| Member | Role |
|---|---|
| Abdelrahman Essam El-Sayed | Backend development, Python, data engineering, scientific data processing |
| Noor Tarek Mohamed | Frontend development, React, UI, data visualization |
| Shams Tarek Mohamed | Research, scientific documentation, experiment logging, presentation |

## 19. Acknowledgements

- NASA Space Apps Challenge, for the challenge and the opportunity.
- NASA FIRMS and the teams behind the MODIS and VIIRS active-fire products.
- NASA LANCE and ESDIS, for data distribution.

This project is an independent team submission and is not endorsed by NASA.

## 20. License

This project is released under a custom team license. See the [LICENSE](LICENSE) file. The license does not apply to NASA data or third-party software, which remain under their own terms.

> If the NASA Space Apps Challenge requires a specific license or grants rights to NASA or the public, those requirements take precedence. See the LICENSE file for details.

## 21. Project Status

> `TODO`: Update this table honestly as work progresses.

| Component | Status |
|---|---|
| FIRMS data ingestion | Planned |
| Schema normalization with provenance | Planned |
| Spatial harmonization | Planned |
| Temporal harmonization | Planned |
| FRP comparison | Planned |
| Historical activity analysis | Planned |
| Anomaly detection | Planned |
| Frontend visualization | Planned |
| Validation | Planned |
| Public API | Not defined |
