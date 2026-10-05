# System Architecture Document
## AI Powered Water Recharge

| | |
|---|---|
| **Document Version** | 1.0 |
| **Companion Document** | AI_Powered_Water_Recharge_PRD.md |
| **Architecture Style** | Modular monolith (service-oriented internally), containerized, cloud-native data ingestion |
| **Status** | Draft for Panel Review |

---

## 1. Architecture Principles

This system is designed around five guiding principles, chosen specifically for a free-tier, student-built, 12-month academic project:

1. **Software-only, zero hardware** — every data need is satisfied by satellite platforms or existing government sensor networks, never by devices we build or deploy.
2. **Cost-zero by design** — every technology choice must operate within a free tier (Google Earth Engine, free-tier hosting, open-source libraries).
3. **Modular over monolithic-in-spirit** — each of the four intelligence modules (Recommendation, Explainability, Verification, Quality Screening) is built as an independently testable component behind a shared API layer, even though they may be deployed together as one service for simplicity.
4. **Explainability is architectural, not optional** — the explainability layer is wired directly into the inference path of every model-producing module, not bolted on afterward.
5. **Batch/scheduled over real-time streaming** — since groundwater changes slowly, the architecture favors scheduled data refresh (daily/periodic) over complex real-time streaming infrastructure, which would add cost and complexity with no real benefit.

---

## 2. High-Level System Architecture

```mermaid
flowchart TB
    subgraph EXT["External Data Sources (Free Tier)"]
        GEE["Google Earth Engine<br/>Sentinel-1/2, Landsat, MODIS, SRTM"]
        CHIRPS["CHIRPS Rainfall"]
        GRACE["GRACE-FO<br/>(NASA/JPL)"]
        BHUVAN["Bhuvan (ISRO)"]
        WRIS["India-WRIS / CGWB WIMS<br/>(ground-truth well data)"]
    end

    subgraph ING["Data Ingestion Layer"]
        SCHED["Scheduler<br/>(GitHub Actions / cron)"]
        FETCH["Fetch Scripts<br/>(Python: GEE API, requests, CKAN API)"]
    end

    subgraph STORE["Storage Layer"]
        PG[("PostgreSQL + PostGIS")]
        ASSETS[("GEE Assets<br/>(cached processed layers)")]
    end

    subgraph ML["Intelligence Layer"]
        M1["Module 1<br/>Site Recommendation<br/>(XGBoost / Random Forest)"]
        M2["Module 2<br/>Explainability<br/>(SHAP / LIME)"]
        M3["Module 3<br/>Verification & Monitoring<br/>(LSTM / Bi-LSTM)"]
        M4["Module 4<br/>Water Quality Risk<br/>(RF/XGBoost + GIS buffer)"]
    end

    subgraph API["Backend API Layer"]
        FASTAPI["FastAPI REST Service"]
    end

    subgraph FE["Frontend Layer"]
        REACT["React.js Dashboard"]
        LEAFLET["Leaflet.js Map Interface"]
    end

    USER["District Officer / Panchayat User"]

    GEE --> FETCH
    CHIRPS --> FETCH
    GRACE --> FETCH
    BHUVAN --> FETCH
    WRIS --> FETCH
    SCHED --> FETCH
    FETCH --> PG
    FETCH --> ASSETS

    PG --> M1
    ASSETS --> M1
    PG --> M3
    M1 --> M2
    M1 --> M4
    PG --> M4

    M1 --> FASTAPI
    M2 --> FASTAPI
    M3 --> FASTAPI
    M4 --> FASTAPI

    FASTAPI --> REACT
    REACT --> LEAFLET
    USER --> REACT
```

---

## 3. Component Architecture

### 3.1 Module 1 — Site Recommendation Engine

**Responsibility:** Given a region, produce a ranked list of geographic candidate points for new recharge structures.

```mermaid
flowchart LR
    A["Region Input<br/>(polygon/district)"] --> B["Feature Extraction<br/>(slope, soil, LULC, rainfall,<br/>drainage, geology)"]
    B --> C["Feature Vector<br/>per Grid Cell"]
    C --> D["Trained XGBoost<br/>Classifier"]
    D --> E["Suitability Score<br/>(0-1) per Cell"]
    E --> F["Rank & Filter<br/>Top-N Sites"]
    F --> G["Output: Ranked<br/>Site List + Map Layer"]
```

- **Input:** GeoJSON polygon or district identifier
- **Processing:** Pulls cached feature layers from PostGIS/GEE Assets, builds a per-grid-cell feature vector, scores each cell
- **Output:** Ranked site list (lat/lon + score), GeoJSON suitability layer
- **Model refresh policy:** Manually triggered retraining for MVP; scheduled monthly retraining as a stretch goal

### 3.2 Module 2 — Explainability Layer

**Responsibility:** Attach a human-readable justification to every score Module 1 produces.

```mermaid
flowchart LR
    A["Model + Feature Vector<br/>(from Module 1)"] --> B["SHAP TreeExplainer"]
    B --> C["Per-Feature<br/>Contribution Values"]
    C --> D["Template Engine<br/>(rule-based sentence builder)"]
    D --> E["Plain-Language<br/>Explanation String"]
```

- **Input:** Trained model object + the specific feature vector for one site
- **Processing:** SHAP computes marginal contribution of each feature; top 2–3 contributing factors are converted into a sentence template (e.g., `"High suitability due to {factor_1} and {factor_2}"`)
- **Output:** JSON object `{site_id, shap_values, explanation_text}`
- **Design note:** This module never runs standalone — it is invoked immediately after Module 1 produces a score, so every recommendation is explainable by construction, not by later addition

### 3.3 Module 3 — Recharge Verification & Monitoring

**Responsibility:** Determine whether a specific structure is actually producing a measurable groundwater recharge effect.

```mermaid
flowchart LR
    A["Historical Well Readings<br/>(near structure)"] --> B["Bi-LSTM<br/>Forecast Model"]
    B --> C["Predicted Trend<br/>(expected level over time)"]
    D["New Actual Readings<br/>(scheduled fetch)"] --> E["Deviation Check<br/>(predicted vs actual)"]
    C --> E
    E --> F{"Deviation ><br/>Threshold?"}
    F -->|Yes| G["Flag: Underperforming"]
    F -->|No| H["Status: OK"]
    G --> I["verification_logs table"]
    H --> I
```

- **Input:** Structure ID, associated nearby well IDs, historical + newly fetched readings
- **Processing:** Bi-LSTM forecasts the expected level trajectory; each scheduled refresh compares new actual data against the forecast
- **Output:** Status flag (OK / Underperforming) + logged history entry
- **Trigger:** Runs on the same scheduled cadence as the India-WRIS data refresh job (daily/periodic)

### 3.4 Module 4 — Water Quality Risk Screener

**Responsibility:** Assign a contamination risk category to a candidate site before it is finalized as a recommendation.

```mermaid
flowchart LR
    A["Candidate Site<br/>Coordinates"] --> B["Proximity Analysis<br/>(GIS buffer: farmland,<br/>industrial zone, sewage line)"]
    B --> C["Risk Feature Vector"]
    C --> D["RF/XGBoost<br/>Risk Classifier"]
    D --> E["Risk Category<br/>(Low / Medium / High)"]
```

- **Input:** Candidate site coordinates from Module 1
- **Processing:** GIS buffer analysis computes distance-based features; classifier assigns a risk category
- **Output:** Risk label attached to the site record before it's surfaced to the frontend

---

## 4. Data Flow Architecture

```mermaid
sequenceDiagram
    participant Sched as Scheduler
    participant Fetch as Fetch Service
    participant GEE as Google Earth Engine
    participant WRIS as India-WRIS/WIMS
    participant DB as PostgreSQL+PostGIS
    participant ML as ML Modules
    participant API as FastAPI
    participant UI as React Dashboard

    Sched->>Fetch: Trigger daily job
    Fetch->>GEE: Request satellite layers (cached where possible)
    GEE-->>Fetch: Return processed layer references
    Fetch->>WRIS: Request latest well readings (CSV/CKAN)
    WRIS-->>Fetch: Return new readings
    Fetch->>DB: Upsert new data (change-detected only)
    DB-->>ML: Provide feature vectors + well readings
    ML->>ML: Score sites (M1) -> explain (M2) -> verify (M3) -> risk-screen (M4)
    ML->>DB: Persist results (sites, explanations, verification_logs)
    UI->>API: Request region results
    API->>DB: Query latest site/verification data
    DB-->>API: Return results
    API-->>UI: JSON response
    UI->>UI: Render map + detail panels (Leaflet)
```

---

## 5. API Architecture (REST Endpoints)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/regions` | List selectable regions (state/district) |
| `POST` | `/api/v1/sites/recommend` | Run/retrieve site recommendations for a given region polygon |
| `GET` | `/api/v1/sites/{site_id}` | Get full detail for a single site (score, explanation, risk) |
| `GET` | `/api/v1/sites/{site_id}/explanation` | Get SHAP-based explanation for a site |
| `GET` | `/api/v1/structures/{structure_id}/verification` | Get verification history/status for a built structure |
| `POST` | `/api/v1/structures` | Register a newly built structure against a recommended site |
| `GET` | `/api/v1/wells/{well_id}/readings` | Get historical readings for a well |
| `GET` | `/api/v1/data-refresh/status` | Get last successful ingestion run timestamp per source |
| `GET` | `/api/v1/health` | Service health check |

**API design notes:**
- All endpoints return JSON; geospatial results additionally support GeoJSON via an `?format=geojson` query parameter for direct Leaflet consumption.
- Long-running recommendation requests (large regions) are handled asynchronously: `POST /sites/recommend` returns a `job_id` immediately, with results polled via `GET /api/v1/jobs/{job_id}`.
- Authentication is out of scope for the academic MVP (single-tenant demo deployment); noted as a future-scope item for production use.

---

## 6. Database Architecture (Entity Relationships)

```mermaid
erDiagram
    SITES ||--o{ SITE_FEATURES : has
    SITES ||--o| EXPLANATIONS : has
    SITES ||--o| STRUCTURES : "becomes (if built)"
    STRUCTURES ||--o{ VERIFICATION_LOGS : generates
    WELLS ||--o{ WELL_READINGS : records
    STRUCTURES }o--o{ WELLS : "monitored-by (nearby)"

    SITES {
        uuid site_id PK
        float latitude
        float longitude
        string region
        float suitability_score
        string risk_category
        datetime created_at
    }
    SITE_FEATURES {
        uuid site_id FK
        float slope
        string soil_type
        string land_use
        float rainfall
        float drainage_density
        string geology
    }
    EXPLANATIONS {
        uuid site_id FK
        json shap_values
        text plain_text_summary
    }
    STRUCTURES {
        uuid structure_id PK
        uuid site_id FK
        date build_date
        string structure_type
    }
    VERIFICATION_LOGS {
        uuid structure_id FK
        date check_date
        float predicted_level
        float actual_level
        string status
    }
    WELLS {
        uuid well_id PK
        float latitude
        float longitude
        string source
        string region
    }
    WELL_READINGS {
        uuid well_id FK
        date reading_date
        float water_level
        datetime source_updated_at
    }
```

---

## 7. Data Ingestion & Scheduling Architecture

| Job | Frequency | Source | Mechanism |
|---|---|---|---|
| Satellite layer refresh | Weekly (or on-demand for prototyping) | GEE (Sentinel, Landsat, MODIS, SRTM) | GEE Python API script, results cached as GEE Assets |
| Rainfall data refresh | Monthly | CHIRPS | GEE or direct CHC bulk download |
| Groundwater storage refresh | Monthly | GRACE-FO | Direct NASA/JPL download script |
| Well-level data refresh | Daily | India-WRIS / India Data Portal (CKAN) | Scheduled fetch script with change-detection (timestamp/hash comparison) |
| Verification re-check | Daily (same trigger as well-level refresh) | Internal (Module 3) | Runs immediately after new well data lands |
| Model retraining | Manual (MVP) / Monthly (stretch) | Internal | Triggered script; stores versioned model artifact |

**Change-detection strategy:** Rather than reprocessing all data on every run, the fetch service compares the source's last-modified timestamp (or a content hash) against the `data_refresh_log` table and only ingests genuinely new records — this keeps both database writes and GEE compute usage minimal.

---

## 8. Deployment Architecture

```mermaid
flowchart TB
    subgraph DOCKER["Docker Compose (local dev) / Container Host (deployed)"]
        C1["Container: FastAPI Backend<br/>+ ML inference modules"]
        C2["Container: PostgreSQL + PostGIS"]
        C3["Container: React Frontend<br/>(served via Nginx or static host)"]
        C4["Container: Scheduler<br/>(cron-based fetch jobs)"]
    end

    C4 -->|writes| C2
    C1 -->|reads/writes| C2
    C3 -->|calls REST API| C1

    HOST["Free-Tier Hosting<br/>(Render / Streamlit Community Cloud)"]
    GH["GitHub Actions<br/>(scheduled data-refresh jobs)"]

    DOCKER --> HOST
    GH -.->|triggers, if not using in-container cron| C4
```

- **Local development:** `docker-compose` spins up all four containers together for development/testing.
- **Deployed environment:** Backend + database deployed to a free-tier host (Render); scheduled ingestion jobs run via GitHub Actions rather than an always-on container, to avoid consuming free-tier compute hours unnecessarily.
- **Frontend:** Built as a static React bundle, served independently (Render static site or Streamlit Community Cloud, depending on final framework choice).

---

## 9. Security & Configuration Architecture

| Concern | Approach |
|---|---|
| API keys / credentials (GEE service account, NASA Earthdata login) | Stored as environment variables / repository secrets, never committed to source control |
| Database credentials | Environment variables, injected at container runtime |
| Public data exposure | All source data used is already publicly published government/satellite data; no personally identifiable information is collected or stored |
| Input validation | All FastAPI endpoints use Pydantic models for strict request validation |
| Rate-limiting external calls | Fetch scripts implement backoff/retry logic and respect a conservative polling frequency (daily, not aggressive) to avoid overloading public government portals |

---

## 10. Repository / Folder Structure

```
ai-powered-water-recharge/
├── backend/
│   ├── app/
│   │   ├── api/                 # FastAPI route definitions
│   │   ├── models/               # Pydantic request/response schemas
│   │   ├── ml/
│   │   │   ├── module1_recommendation/
│   │   │   ├── module2_explainability/
│   │   │   ├── module3_verification/
│   │   │   └── module4_risk_screening/
│   │   ├── db/                   # SQLAlchemy models, migrations
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── ingestion/
│   ├── fetch_gee_layers.py
│   ├── fetch_chirps.py
│   ├── fetch_grace_fo.py
│   ├── fetch_india_wris.py
│   └── scheduler_config.yml       # GitHub Actions workflow definitions
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── notebooks/                     # Model training/experimentation notebooks
├── docs/
│   ├── AI_Powered_Water_Recharge_PRD.md
│   ├── AI_Powered_Water_Recharge_Architecture.md
│   └── Literature_Review.pdf
├── docker-compose.yml
└── README.md
```

---

## 11. Error Handling & Monitoring

| Layer | Strategy |
|---|---|
| Data ingestion scripts | Try/except around every external call; failures logged to `data_refresh_log` with status and error message, not silently swallowed |
| GEE quota exhaustion | Fetch scripts check remaining quota where possible; gracefully degrade to cached/last-known-good data rather than failing the whole pipeline |
| ML inference errors | API layer returns a structured error response (HTTP 4xx/5xx with message) rather than an unhandled exception |
| Frontend | Displays a clear "data temporarily unavailable" state rather than a blank map if the backend call fails |
| Monitoring (lightweight, free) | GitHub Actions job status serves as the primary ingestion health signal; optional Google Cloud Monitoring alert on GEE quota threshold |

---

## 12. Scalability Considerations (Beyond Academic Scope)

Documented for completeness / future-scope discussion with the panel, not required for MVP delivery:

- Moving from PostgreSQL to a managed geospatial database service for multi-state concurrent usage
- Introducing a message queue (e.g., Celery + Redis) for asynchronous large-region processing jobs
- Adding authentication/role-based access for multi-department real-world deployment
- Moving scheduled ingestion from GitHub Actions to a dedicated orchestration tool (Airflow) at larger scale

---

## 13. Architecture-to-Objective Traceability

| Objective (from PRD) | Architecture Component |
|---|---|
| O1 — Site Recommendation | Module 1, Data Ingestion Layer, Storage Layer |
| O2 — Explainability | Module 2 (chained directly after Module 1 in the inference path) |
| O3 — Verification | Module 3, scheduled well-data refresh job, verification_logs table |
| O4 — Quality Risk Screening | Module 4, GIS buffer analysis component |
| O5 — Deployed Platform | Backend API Layer + Frontend Layer + Deployment Architecture |

---

*End of Document*
