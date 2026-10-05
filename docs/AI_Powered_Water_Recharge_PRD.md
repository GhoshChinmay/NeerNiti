# Project Requirements Document (PRD)
## AI Powered Water Recharge

| | |
|---|---|
| **Document Version** | 1.0 |
| **Project Type** | Final Year Major Project (Data Science & Machine Learning) |
| **Development Timeline** | 12 months |
| **Document Owner** | Chinmay Ghosh |
| **Status** | Draft for Panel Review |
| **Base Paper** | Patidar, N., Yadav, B., Kumar, S. et al. (2023). *A Web-Enabled Tool for Site Suitability Mapping for Managed Aquifer Recharge (MAR) using Google Earth Engine (GEE) and Multi-Criteria Decision Analysis (MCDA)*. Water Resources Management, 37(14), 5619–5634. |

---

## 1. Executive Summary

AI Powered Water Recharge is a fully software-based, AI-driven decision-support system that solves two unresolved problems in India's groundwater management landscape: **(a)** where new artificial recharge structures should be built, and **(b)** whether existing structures are actually recharging groundwater. The system replaces manual, expert-dependent GIS overlay methods with a trained, explainable machine-learning pipeline, layered on top of free satellite and government datasets, and delivered as a deployable web platform. No physical hardware, sensors, or IoT devices are used or required — the system consumes data that satellites and existing government sensor networks already produce.

This document defines the functional and non-functional requirements, system architecture, technology stack, data sources, and delivery plan for building this system within a 12-month academic development cycle.

---

## 2. Problem Statement

India has constructed an estimated 2.76 million artificial recharge structures against an original target of 1 million, yet roughly 14% of the country's groundwater assessment units remain over-exploited. This gap exists because of three unresolved, well-documented problems:

1. **Site selection is manual, slow, and inconsistent** — practitioners overlay GIS layers (geology, slope, land use) and assign suitability weights by hand using the Analytic Hierarchy Process (AHP), a method that varies between experts and does not update automatically as new data becomes available.
2. **Construction is tracked, but outcomes are not** — India measures success by counting structures built, not by verifying whether groundwater levels near those structures have actually improved.
3. **Existing digital tools stop at recommendation, not verification** — the most advanced deployed system in this space (G-MCDA, our base paper) automates site suitability scoring but uses static, rule-based MCDA rather than a learned model, and includes no mechanism to verify post-construction outcomes.

---

## 3. Goals & Objectives

| # | Objective | Primary SOTA Technology |
|---|---|---|
| O1 | Automatically recommend optimal sites for new recharge structures using satellite-derived features and a trained ML model | XGBoost, Random Forest, Google Earth Engine |
| O2 | Make every AI recommendation explainable in plain language for non-technical stakeholders | SHAP, LIME |
| O3 | Verify whether existing and newly built structures are actually recharging groundwater over time | LSTM / Bi-LSTM, GRACE-FO satellite data |
| O4 | Screen every recommended site for groundwater contamination risk before approval | Random Forest/XGBoost classification, GIS buffer analysis |
| O5 | Deliver the system as one deployable, usable web platform, not a research artifact | FastAPI, React.js, Leaflet.js |

---

## 4. Scope

### 4.1 In Scope (Core MVP — must be delivered)
- Site suitability recommendation engine (single-country, India-wide, region-configurable)
- Explainability layer attached to every model prediction
- Groundwater recharge verification/monitoring module using time-series forecasting
- A deployed web dashboard integrating the above three modules
- Water quality contamination risk screening for recommended sites

### 4.2 In Scope (Stretch Goals — build if time permits)
- Abandoned borewell-to-recharge-point identification module
- Simplified self-retraining/model-refresh pipeline triggered by new satellite data

### 4.3 Out of Scope (explicitly excluded, documented for panel clarity)
- Any physical sensor, IoT device, or hardware deployment of any kind
- Real-time (sub-daily) data ingestion — the system uses scheduled daily/periodic refresh, appropriate to groundwater's slow rate of change
- Upstream-downstream water conflict causal modeling (documented as future scope only)
- Citizen crowdsourcing mobile app (documented as future scope only)
- Commercial-scale, multi-country deployment

---

## 5. Stakeholders & Target Users

| Stakeholder | Role / Interest |
|---|---|
| District Groundwater/Irrigation Officers | Primary end users — use the dashboard to plan new recharge structures |
| Gram Panchayat Officials | Secondary users — view recommendations and monitoring alerts for their village |
| Academic Panel / Evaluators | Assess technical rigor, novelty, and feasibility |
| Project Developer (Student) | Designs, builds, trains, and deploys the system |
| Central/State Groundwater Boards (indirect) | Data providers (CGWB, India-WRIS) — not active system users in v1 |

---

## 6. Functional Requirements

### 6.1 Module 1 — Site Recommendation Engine

| ID | Requirement |
|---|---|
| FR-1.1 | System shall accept a geographic region (state/district/custom polygon) as input and output a ranked list of candidate recharge sites |
| FR-1.2 | System shall compute suitability scores using at minimum: slope, soil type, land use/land cover, drainage density, rainfall, geology, depth to groundwater |
| FR-1.3 | System shall support region-specific model behavior (e.g., hard-rock vs. alluvial terrain) rather than a single national formula |
| FR-1.4 | System shall retrain or re-score when underlying satellite layers are refreshed |
| FR-1.5 | System shall output results as both a downloadable map layer (GeoJSON/raster) and a ranked list with coordinates |

### 6.2 Module 2 — Explainability Layer

| ID | Requirement |
|---|---|
| FR-2.1 | Every site recommendation shall include a SHAP-based feature contribution breakdown |
| FR-2.2 | System shall convert SHAP values into a plain-language sentence (e.g., "High suitability due to steep slope and low clay content") |
| FR-2.3 | Explainability output shall be viewable per-site on the dashboard without requiring technical ML knowledge to interpret |

### 6.3 Module 3 — Recharge Verification & Monitoring

| ID | Requirement |
|---|---|
| FR-3.1 | System shall forecast expected groundwater level trends near a given structure using historical well data |
| FR-3.2 | System shall compare forecasted vs. actual observed groundwater levels on a recurring schedule (minimum: monthly) |
| FR-3.3 | System shall flag any structure whose actual trend deviates significantly (configurable threshold) from the forecasted trend as "underperforming" |
| FR-3.4 | System shall maintain a historical log of verification results per structure for trend analysis |

### 6.4 Module 4 — Water Quality Risk Screener

| ID | Requirement |
|---|---|
| FR-4.1 | System shall compute proximity of a candidate site to known pollution sources (farmland, industrial zones, sewage lines) |
| FR-4.2 | System shall assign a contamination risk category (Low/Medium/High) to every recommended site |
| FR-4.3 | Sites flagged High risk shall be visually distinguished on the dashboard map |

### 6.5 Module 5 — Web Dashboard

| ID | Requirement |
|---|---|
| FR-5.1 | System shall provide an interactive map interface showing recommended sites, risk levels, and verification status |
| FR-5.2 | System shall allow a user to select a region and view/download recommendation results |
| FR-5.3 | System shall provide a per-site detail view showing suitability score, explanation, risk rating, and monitoring history |
| FR-5.4 | System shall be accessible via standard web browser, no client installation required |

### 6.6 Data Ingestion (Cross-cutting)

| ID | Requirement |
|---|---|
| FR-6.1 | System shall ingest satellite layers (Sentinel-1/2, Landsat, MODIS, SRTM) via Google Earth Engine |
| FR-6.2 | System shall ingest rainfall data (CHIRPS) and groundwater storage anomaly data (GRACE-FO) |
| FR-6.3 | System shall ingest ground-truth groundwater well data from India-WRIS/CGWB WIMS on a scheduled basis (daily or better) |
| FR-6.4 | System shall cache/store processed satellite layers as reusable assets to minimize redundant compute |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Site recommendation query for a district-scale region shall return results within 60 seconds under normal GEE quota conditions |
| **Scalability** | System architecture shall support scaling from single-district to state-wide analysis without redesign |
| **Availability** | Dashboard shall target 95% uptime on free-tier hosting during the academic evaluation period |
| **Usability** | Non-technical users (district officers) shall be able to interpret a recommendation without ML training |
| **Cost** | Entire system shall operate within free-tier limits of all third-party services (no paid infrastructure required) |
| **Maintainability** | Codebase shall be modular (separate services per module) to allow independent updates |
| **Portability** | System shall be containerized (Docker) to ensure reproducible deployment |
| **Data Freshness** | Satellite and well data shall be refreshed on a scheduled (minimum daily) basis, not real-time streaming |
| **Explainability** | No model output shall be presented to end users without an accompanying explanation |
| **Security** | All data-source API credentials shall be stored as environment variables/secrets, never hardcoded |

---

## 8. System Architecture Overview

```
                     ┌────────────────────────────┐
                     │   Data Sources (External)    │
                     │  GEE / Copernicus / USGS /    │
                     │  NASA Earthdata / CHIRPS /    │
                     │  Bhuvan / India-WRIS / WIMS   │
                     └──────────────┬─────────────┘
                                    │ scheduled fetch (cron / GitHub Actions)
                                    ▼
                     ┌────────────────────────────┐
                     │     Data Ingestion Layer      │
                     │  Python fetch scripts +       │
                     │  GEE Python API + CKAN API    │
                     └──────────────┬─────────────┘
                                    ▼
                     ┌────────────────────────────┐
                     │   Processing & Storage Layer  │
                     │  PostgreSQL + PostGIS         │
                     │  GEE Assets (cached layers)   │
                     └──────────────┬─────────────┘
                                    ▼
        ┌──────────────┬───────────┴───────────┬──────────────┐
        ▼              ▼                       ▼              ▼
┌───────────────┐ ┌──────────────┐   ┌──────────────────┐ ┌───────────────┐
│ Module 1        │ │ Module 2       │   │ Module 3            │ │ Module 4        │
│ Site Recomm.     │ │ Explainability │   │ Verification/Monitor│ │ Quality Screener│
│ XGBoost/RF        │ │ SHAP/LIME      │   │ LSTM/Bi-LSTM        │ │ RF/XGBoost + GIS│
└───────┬───────┘ └──────┬───────┘   └────────┬─────────┘ └───────┬───────┘
        └──────────────┴────────────┬─────────┴──────────────────┘
                                    ▼
                     ┌────────────────────────────┐
                     │     Backend API Layer         │
                     │        FastAPI (REST)         │
                     └──────────────┬─────────────┘
                                    ▼
                     ┌────────────────────────────┐
                     │   Frontend Dashboard          │
                     │   React.js + Leaflet.js       │
                     └────────────────────────────┘
```

---

## 9. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| Satellite/geospatial processing | Google Earth Engine (Python API) | Free academic tier, industry-standard for large-scale remote sensing |
| ML — Site Recommendation | XGBoost, Random Forest (scikit-learn) | Highest benchmarked accuracy across reviewed literature |
| ML — Verification/Forecasting | LSTM / Bi-LSTM (TensorFlow or PyTorch) | Best-performing architecture for groundwater time-series forecasting per literature review |
| Explainability | SHAP, LIME | Industry-standard, model-agnostic interpretability |
| Backend framework | FastAPI (Python) | Async-native, integrates directly with the ML/data stack |
| Frontend framework | React.js | Component-based, widely supported |
| Mapping library | Leaflet.js | Free, lightweight, sufficient for suitability map rendering |
| Database | PostgreSQL + PostGIS extension | Native geospatial query support, free and open-source |
| Scheduling/automation | GitHub Actions (scheduled workflows) or cron | Free tier sufficient for daily data-refresh jobs |
| Containerization | Docker | Reproducible deployment, portable across environments |
| Hosting (demo/deployment) | Render / Streamlit Community Cloud (free tier) | No-cost deployment suitable for academic demonstration |
| Version control | Git + GitHub | Standard practice, free for public/academic repos |

---

## 10. External Data Sources & Access Method

| Data Source | Purpose | Access Method | Free Tier Constraint |
|---|---|---|---|
| Sentinel-1/2 (Copernicus) | Soil moisture, land use, vegetation | Google Earth Engine | Subject to GEE EECU-hour quota |
| Landsat 8/9 (USGS) | Long-term land-cover change | Google Earth Engine / EarthExplorer | Subject to GEE quota |
| SRTM / Cartosat DEM | Elevation, slope | Google Earth Engine / Bhuvan | Subject to GEE quota |
| MODIS (NASA) | Land surface temperature, evapotranspiration | Google Earth Engine / NASA Earthdata | Subject to GEE quota |
| CHIRPS Rainfall | Rainfall input, climate-adaptive scoring | Google Earth Engine or direct CHC download | None significant at project scale |
| GRACE-FO (NASA/JPL) | Groundwater storage change signal | Direct NASA/JPL portal download | None significant; coarse resolution (~25km) |
| Bhuvan (ISRO) | India-specific geology, groundwater prospect layers | Direct portal download | None; manual download only |
| India-WRIS / CGWB WIMS | Ground-truth well-level data (training labels) | Direct portal export (CSV/Excel) or India Data Portal CKAN API | No documented real-time API; scheduled bulk pulls used instead |

**GEE quota management:** Project will request the free Contributor Tier (1,000 EECU-hours/month) on project start. Development practices (district-scale prototyping, cached GEE Assets, seasonal composites instead of full daily time-series) are followed throughout to stay within this budget — detailed in the project's Quota Management Appendix.

---

## 11. Database Design (High-Level Schema)

| Table | Key Fields | Purpose |
|---|---|---|
| `sites` | site_id, latitude, longitude, region, suitability_score, risk_category, created_at | Stores every recommended site and its scores |
| `site_features` | site_id, slope, soil_type, land_use, rainfall, drainage_density, geology | Stores raw feature values used for scoring |
| `explanations` | site_id, shap_values (JSON), plain_text_summary | Stores explainability output per site |
| `wells` | well_id, latitude, longitude, source (CGWB/India-WRIS), region | Ground-truth well station registry |
| `well_readings` | well_id, reading_date, water_level, source_updated_at | Time-series of actual observed groundwater levels |
| `structures` | structure_id, site_id, build_date, structure_type | Registry of constructed recharge structures |
| `verification_logs` | structure_id, check_date, predicted_level, actual_level, status (OK/Underperforming) | Monitoring history per structure |
| `data_refresh_log` | source_name, last_fetched_at, status | Tracks scheduled data ingestion runs |

---

## 12. Machine Learning Requirements

| Requirement | Detail |
|---|---|
| Training data | Historical CGWB/India-WRIS well readings labeled against known high/low groundwater zones |
| Train/test split | Spatial cross-validation (not random split) to avoid geographic data leakage |
| Baseline models | Logistic Regression / simple Random Forest as accuracy baseline |
| Primary model | XGBoost (Module 1), Bi-LSTM (Module 3) |
| Evaluation metrics | AUC-ROC, F1-score (Module 1 classification); RMSE, MAE (Module 3 forecasting) |
| Explainability requirement | Every production model must support SHAP value extraction |
| Retraining trigger | Manual trigger for MVP; scheduled monthly retraining as stretch goal |
| Model versioning | Store trained model artifacts with timestamp and training-data snapshot reference |

---

## 13. Assumptions & Constraints

- The project team consists of student developer(s) with no dedicated infrastructure budget; all tools/services used must be free-tier.
- India-WRIS/CGWB do not provide a documented real-time public API; the system relies on scheduled bulk data pulls rather than live streaming.
- Groundwater level change is physically gradual; daily/periodic data refresh is treated as functionally equivalent to "real-time" for this domain.
- Google Earth Engine's Noncommercial Quota Tier policy (effective April 2026) applies; project will operate under the Contributor Tier.
- No physical hardware, sensors, or field deployment is within scope or budget.

---

## 14. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| GEE compute quota exceeded during heavy development/testing | Medium | Prototype on small regions, cache processed layers as GEE Assets, request Contributor Tier early |
| Sparse/inconsistent ground-truth well data in some regions | Medium | Use spatial interpolation and flag low-confidence regions explicitly rather than silently guessing |
| Government portal (India-WRIS) changes layout, breaking scheduled fetch script | Medium | Build fetch script defensively with error handling/alerts; fall back to manual export if needed |
| Model accuracy varies significantly across India's diverse terrains | High | Train region-aware models/features rather than one national model; document limitation clearly |
| One-year timeline insufficient for all modules | High | Strict MVP scoping (Section 4.1) with stretch goals clearly separated |
| Explainability output too technical for target users | Low-Medium | User-test plain-language explanation templates with non-technical reviewers before final submission |

---

## 15. Success Metrics / Acceptance Criteria

- Module 1 achieves competitive suitability-classification accuracy (target AUC ≥ 0.85, benchmarked against literature-reported ranges of 0.82–0.98)
- Every recommendation displayed on the dashboard includes a non-empty, human-readable explanation
- Module 3 successfully flags at least one verifiably underperforming structure in a test region using historical data
- Dashboard is deployed and publicly accessible via a live URL at project submission
- All data sources used are confirmed free-tier with documented access method (per Section 10)
- Zero physical hardware or IoT components used in the final delivered system

---

## 16. High-Level Timeline (12 Months)

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 1: Literature review, requirements, architecture (this document) | Month 1–2 | Finalized PRD, base paper analysis |
| Phase 2: Data pipeline setup | Month 2–3 | GEE integration, India-WRIS ingestion script, database schema live |
| Phase 3: Module 1 (Site Recommendation) | Month 3–5 | Trained model, validated on test region |
| Phase 4: Module 2 (Explainability) | Month 5–6 | SHAP/LIME integrated into Module 1 output |
| Phase 5: Module 3 (Verification) | Month 6–8 | LSTM forecasting model, verification logic |
| Phase 6: Module 4 (Quality Screener) | Month 8–9 | Risk classification integrated into pipeline |
| Phase 7: Dashboard development | Month 7–10 (parallel) | FastAPI backend + React/Leaflet frontend |
| Phase 8: Integration testing | Month 10–11 | End-to-end system test, bug fixing |
| Phase 9: Deployment & documentation | Month 11–12 | Live deployment, final report, panel presentation |

---

## 17. References

1. Patidar, N., Yadav, B., Kumar, S., Raj, A., Krishan, G., Singh, S., Deka, B.J., Jeong, S., Pandey, A., Matsuno, Y., Singh, R.D. (2023). A web-enabled tool for site suitability mapping for managed aquifer recharge (MAR) using Google Earth Engine (GEE) and multi-criteria decision analysis (MCDA). *Water Resources Management*, 37(14), 5619–5634. — **Base Paper**
2. Full literature survey of 15 papers — see project Literature Review chapter for complete citations.
3. Google Earth Engine — Noncommercial Quota Tiers documentation (effective April 27, 2026).
4. India-WRIS / CGWB WIMS public data portals.
5. India Data Portal — Groundwater dataset (CKAN platform).

---

*End of Document*
