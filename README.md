# Kiddy Spiders \| MODIS--VIIRS Fire Data Harmonization

```{=html}
<p align="center">
```
`<strong>`{=html}Making satellite fire observations more consistent,
comparable, and useful.`</strong>`{=html}
```{=html}
</p>
```
```{=html}
<p align="center">
```
`<em>`{=html}A NASA Space Apps Challenge 2026 project`</em>`{=html}
```{=html}
</p>
```

------------------------------------------------------------------------

## Overview

Satellite instruments observe active fires from different orbits, at
different spatial resolutions, and under different observation
conditions. These differences can make it difficult to compare fire
detections or combine observations into a consistent analytical dataset.

**Kiddy Spiders** is a prototype exploring how active-fire observations
from NASA's MODIS and VIIRS instruments can be processed and harmonized
to support clearer comparison and analysis.

The project focuses on a transparent, reproducible data workflow:
acquiring observations, standardizing their structure, aligning them
across space and time, comparing sensor measurements, and presenting the
results through an interactive interface.

> **Important:** Harmonization does not make MODIS and VIIRS identical
> instruments. The goal is to make their observations more comparable
> while preserving sensor provenance, measurement differences, and
> uncertainty.

## The Challenge

MODIS and VIIRS differ in important ways, including spatial resolution,
instrument characteristics, and observation timing. A direct comparison
of raw detection counts can therefore be misleading.

Our prototype explores three complementary dimensions:

-   **Spatial harmonization** --- organizing observations on a common
    spatial framework while retaining the original sensor and
    measurement information.
-   **Temporal harmonization** --- standardizing acquisition timestamps
    and defining consistent time windows for comparison.
-   **Statistical comparison** --- examining differences in detection
    counts, Fire Radiative Power (FRP), confidence, and sensor
    agreement.

The exact processing choices and validation results should be documented
alongside each experiment.

## Project Goals

-   Combine MODIS and VIIRS active-fire observations in a consistent
    analytical workflow.
-   Preserve the original source sensor and relevant source attributes.
-   Make sensor differences visible instead of hiding them through
    aggregation.
-   Explore unusual changes in observed fire activity using transparent
    statistical methods.
-   Provide an accessible map and analytical dashboard for exploring the
    processed data.
-   Document assumptions, limitations, and validation so results can be
    interpreted responsibly.

## Key Features

The following describes the intended prototype scope. Update feature
status as implementation progresses.

  -----------------------------------------------------------------------
  Feature                             Description
  ----------------------------------- -----------------------------------
  Unified fire map                    Explore geolocated observations and
                                      filter by sensor or time.

  Sensor comparison                   Compare MODIS and VIIRS
                                      observations and selected
                                      measurements.

  Activity calendar                   Explore daily or monthly patterns
                                      in observed fire activity.

  Harmonized dataset                  Access observations with
                                      standardized fields and preserved
                                      provenance.

  Anomaly exploration                 Highlight unusually high observed
                                      activity relative to a defined
                                      historical baseline.

  Data transparency                   Show source, time, confidence, and
                                      relevant processing information.
  -----------------------------------------------------------------------

## Data Sources

The project uses active-fire observations from NASA's Fire Information
for Resource Management System (FIRMS).

-   [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/)
-   [FIRMS API documentation](https://firms.modaps.eosdis.nasa.gov/api/)
-   [FIRMS data
    access](https://firms.modaps.eosdis.nasa.gov/active_fire/)

Potential inputs include MODIS and VIIRS active-fire products made
available through FIRMS. The exact product, processing level, date
range, and download time must be recorded for every dataset used.

### Data provenance

For reproducibility, record at least:

-   Product and sensor name
-   Processing type (for example, near-real-time or standard
    science-quality processing)
-   Acquisition date and time
-   Download date and source
-   Geographic and temporal coverage
-   Relevant product documentation or version

Do not silently mix near-real-time and standard products. Their
processing and availability characteristics may differ.

## Methodology

The processing pipeline is designed around the following stages:

``` text
NASA FIRMS observations
          |
          v
   Data acquisition
          |
          v
   Schema inspection
          |
          v
 Cleaning and normalization
          |
          v
 Spatial and temporal alignment
          |
          v
 Sensor-aware comparison
          |
          v
 Aggregation and analysis
          |
          v
 API + interactive dashboard
```

### 1. Acquisition

Retrieve the selected MODIS and VIIRS active-fire datasets from FIRMS.
Keep the original downloaded files unchanged so that processing can be
reproduced.

### 2. Cleaning and normalization

-   Parse coordinates and acquisition timestamps.
-   Normalize field names and data types.
-   Handle missing or invalid values explicitly.
-   Preserve the original sensor, product, and source attributes.
-   Keep a record of filtering and transformation decisions.

### 3. Spatial alignment

MODIS and VIIRS have different native spatial resolutions. A common grid
may be used for selected comparisons and aggregations.

The grid size and coordinate reference system must be stated in the
methodology. Aggregating observations into a common grid does **not**
create new spatial detail or make the sensors equivalent.

### 4. Temporal alignment

Convert timestamps to a consistent time standard (UTC) and define the
comparison window, such as daily or monthly aggregation. Account for
observation timing when interpreting differences.

### 5. Statistical comparison

Compare appropriate metrics, potentially including:

-   Detection counts per defined area and time window
-   Fire Radiative Power (FRP) distributions and summaries
-   Confidence categories, where available and comparable
-   Spatial and temporal overlap between observations
-   Differences between sensors across matched regions and periods

Avoid interpreting raw detection counts as the number of unique fires.
Multiple detections may relate to the same fire, and detection
opportunities differ between sensors.

### 6. Anomaly exploration

Anomaly indicators can highlight periods with activity above a defined
historical baseline. The baseline, minimum data requirements,
aggregation unit, and threshold should be documented.

An anomaly is a statistical signal for further inspection; it is not, by
itself, a prediction or confirmation of a new fire.

## Technology Stack

### Backend and data processing

-   **Python** --- primary programming language
-   **FastAPI** --- REST API
-   **Pandas / NumPy** --- tabular data processing and numerical
    analysis
-   **GeoPandas / Shapely** --- geospatial processing, where needed
-   **SciPy / scikit-learn** --- optional statistical methods and
    clustering

### Frontend and visualization

-   **React + Vite** --- web application
-   **Leaflet / React-Leaflet** --- interactive maps
-   **Recharts** --- charts and analytical summaries

### Collaboration

-   **Git and GitHub** --- source control and team collaboration
-   **CSV / JSON / GeoJSON** --- data exchange formats

Use only the dependencies required by the implemented workflow. Optional
packages can be added as the prototype evolves.

## Architecture

``` text
                 NASA FIRMS
                     |
             MODIS / VIIRS data
                     |
                     v
          Python processing pipeline
          - acquisition
          - preprocessing
          - harmonization
          - analysis
                     |
                     v
                FastAPI
                     |
              JSON / GeoJSON
                     |
                     v
              React frontend
              - interactive map
              - sensor comparison
              - activity calendar
              - charts
```

## Repository Structure

The structure below is a suggested organization for the prototype.
Adjust it to match the actual repository as implementation evolves.

``` text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── services/
│   │   └── main.py
│   ├── data/
│   │   └── .gitkeep
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docs/
│   ├── methodology.md
│   └── data-sources.md
│
├── .gitignore
├── LICENSE
└── README.md
```

Do not commit API keys, credentials, or large raw datasets. Keep secrets
in environment variables and use an example environment file containing
placeholders only.

## Getting Started

These instructions are a starting point. They assume the backend and
frontend folders follow the suggested structure.

### Requirements

-   Python 3.11 or newer
-   Node.js and npm
-   Git

### 1. Clone the repository

``` bash
git clone <REPOSITORY_URL>
cd <REPOSITORY_DIRECTORY>
```

### 2. Set up the backend

``` bash
cd backend

python -m venv .venv
```

Activate the environment:

**Windows (PowerShell):**

``` powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**

``` cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**

``` bash
source .venv/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Start the API (assuming the FastAPI application is exposed as `app` in
`app/main.py`):

``` bash
uvicorn app.main:app --reload
```

The API should be available at:

-   `http://127.0.0.1:8000`
-   Interactive API documentation: `http://127.0.0.1:8000/docs`

### 3. Set up the frontend

In a separate terminal:

``` bash
cd frontend
npm install
npm run dev
```

Vite will print the local development URL in the terminal.

### 4. Configure data access

If the workflow uses the FIRMS API, obtain a key from the official
[FIRMS MAP_KEY page](https://firms.modaps.eosdis.nasa.gov/api/map_key/).

Store it in an environment variable or an untracked `.env` file. Never
commit a real key.

Example placeholder:

``` env
FIRMS_MAP_KEY=your_key_here
```

The application should also support working with previously downloaded
sample files so that a demo does not depend on live API availability.

## API Overview

The following endpoints are suggested API contracts for the prototype.
An endpoint should only be documented as available once it has actually
been implemented.

  -----------------------------------------------------------------------
  Method                  Endpoint                Purpose
  ----------------------- ----------------------- -----------------------
  `GET`                   `/api/health`           Check API status

  `GET`                   `/api/summary`          Retrieve dataset
                                                  summary statistics

  `GET`                   `/api/hotspots`         Retrieve filtered
                                                  observations for the
                                                  map

  `GET`                   `/api/calendar`         Retrieve aggregated
                                                  activity by time period

  `GET`                   `/api/comparison`       Compare selected MODIS
                                                  and VIIRS metrics

  `GET`                   `/api/anomalies`        Retrieve flagged
                                                  unusual activity
                                                  periods
  -----------------------------------------------------------------------

Suggested query filters include date range, geographic bounds, sensor,
and aggregation interval.

## Validation and Scientific Integrity

A visually convincing map is not enough to establish that a
harmonization method is scientifically reliable.

The team should document:

1.  **Input checks** --- missing values, invalid coordinates, duplicate
    records, and product metadata.
2.  **Method checks** --- grid definition, time-window definition,
    aggregation rules, and transformations.
3.  **Comparison checks** --- matched periods and regions,
    sensor-specific differences, and sensitivity to parameter choices.
4.  **Validation limits** --- what can and cannot be concluded from the
    available observations.

Where possible, compare results against documented product
characteristics and independent reference information. Do not claim
accuracy improvements without a defined validation method and supporting
results.

## Known Limitations

-   MODIS and VIIRS have different instrument characteristics and native
    spatial resolutions.
-   Active-fire products represent satellite detections, not a complete
    inventory of every fire.
-   Clouds, smoke, observation timing, viewing geometry, and other
    conditions can affect detection.
-   A common grid or time window does not eliminate all sensor
    differences.
-   Detection counts should not be treated as counts of unique fire
    events without an appropriate event-matching method.
-   Anomaly flags depend on the selected baseline and thresholds.
-   Results depend on the selected products, date range, geographic
    coverage, and processing choices.

## Team

**Kiddy Spiders --- NASA Space Apps Challenge 2026**

  -----------------------------------------------------------------------
  Team member                         Responsibility
  ----------------------------------- -----------------------------------
  Abdelrahman Essam El-Sayed          Backend development, data
                                      engineering, and harmonization
                                      pipeline

  Noor Tarek Mohamed                  Frontend development and data
                                      visualization

  Shams Tarek Mohamed                 Research, documentation, experiment
                                      logging, and presentation
  -----------------------------------------------------------------------

## Acknowledgements

We acknowledge NASA and the FIRMS team for providing access to
active-fire data and documentation that support this project.

Data attribution and usage must follow the terms and guidance published
by the relevant data provider. NASA data are generally available for
public use, but individual products, imagery, third-party materials, and
services may have additional notices or restrictions. Review the source
documentation before redistribution.

## Project Status

This repository was created for the NASA Space Apps Challenge 2026. It
is a prototype and research exploration, not an operational
fire-monitoring or emergency-response system.

Implementation status, datasets, experiments, and validation results
should be updated as the project develops.

------------------------------------------------------------------------

```{=html}
<p align="center">
```
`<strong>`{=html}Kiddy Spiders`</strong>`{=html}`<br>`{=html}
`<em>`{=html}Different sensors. A clearer picture.`</em>`{=html}
```{=html}
</p>
```
