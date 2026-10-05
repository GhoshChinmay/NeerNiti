# Database Design Document
## AI Powered Water Recharge

| | |
|---|---|
| **Document Version** | 1.0 |
| **Companion Documents** | PRD.md, Architecture.md, Design.md, Rules.md, Phases.md |
| **Database Engine** | PostgreSQL 15+ with PostGIS extension |
| **Scope** | Complete schema: ERD, full DDL, data dictionary, indexing, normalization, query patterns, retention policy |
| **Status** | Draft for Panel Review |

---

## 1. Design Goals

1. **Geospatial-native** — every table that represents a physical location stores real geospatial types (`GEOGRAPHY`/`GEOMETRY` via PostGIS), not just plain latitude/longitude floats, so proximity and containment queries (Module 4's buffer analysis, Module 3's "nearest well" lookup) run natively in the database rather than in application code.
2. **Traceability by default** — every prediction, explanation, and verification result is linked back to the exact model version that produced it, so results are reproducible and defensible during a panel defense.
3. **Idempotent ingestion** — schema constraints (unique keys, upserts) are designed so that re-running a scheduled fetch job never creates duplicate data, per Rules.md Section 6.
4. **Free-tier friendly** — normalized to 3NF to minimize storage footprint (relevant since free-tier hosted Postgres instances typically cap storage in the low single-digit GBs).

---

## 2. Complete Entity-Relationship Diagram

```mermaid
erDiagram
    REGIONS ||--o{ SITES : contains
    REGIONS ||--o{ WELLS : contains
    SITES ||--|| SITE_FEATURES : has
    SITES ||--o| EXPLANATIONS : has
    SITES ||--o| STRUCTURES : "becomes (if built)"
    STRUCTURES ||--o{ VERIFICATION_LOGS : generates
    STRUCTURES }o--o{ WELLS : "monitored via"
    STRUCTURES }o--|| STRUCTURE_WELLS : links
    WELLS ||--o{ WELL_READINGS : records
    MODEL_VERSIONS ||--o{ SITES : "scored by"
    MODEL_VERSIONS ||--o{ VERIFICATION_LOGS : "forecast by"
    DATA_REFRESH_LOG }o--|| REGIONS : "tracks refresh for"

    REGIONS {
        uuid region_id PK
        string region_name
        string region_type
        string state
        geometry boundary_geom
    }
    SITES {
        uuid site_id PK
        uuid region_id FK
        geography location
        float suitability_score
        string risk_category
        string model_version_id FK
        timestamp created_at
    }
    SITE_FEATURES {
        uuid site_id PK_FK
        float slope_deg
        string soil_type
        string land_use
        float rainfall_mm
        float drainage_density
        string geology_type
        float depth_to_groundwater_m
    }
    EXPLANATIONS {
        uuid explanation_id PK
        uuid site_id FK
        jsonb shap_values
        text plain_text_summary
        timestamp generated_at
    }
    STRUCTURES {
        uuid structure_id PK
        uuid site_id FK
        date build_date
        string structure_type
        string status
    }
    STRUCTURE_WELLS {
        uuid structure_id PK_FK
        uuid well_id PK_FK
        float distance_m
    }
    WELLS {
        uuid well_id PK
        uuid region_id FK
        geography location
        string source
        string cgwb_station_code
    }
    WELL_READINGS {
        uuid reading_id PK
        uuid well_id FK
        date reading_date
        float water_level_m
        timestamp source_updated_at
    }
    VERIFICATION_LOGS {
        uuid log_id PK
        uuid structure_id FK
        string model_version_id FK
        date check_date
        float predicted_level_m
        float actual_level_m
        float deviation_pct
        string status
    }
    MODEL_VERSIONS {
        string model_version_id PK
        string module_name
        string algorithm
        date trained_on
        jsonb hyperparameters
        jsonb evaluation_metrics
        string training_data_snapshot
    }
    DATA_REFRESH_LOG {
        uuid log_id PK
        uuid region_id FK
        string source_name
        timestamp fetched_at
        string status
        text error_message
    }
```

---

## 3. Normalization Rationale

The schema is normalized to **Third Normal Form (3NF)** with two deliberate exceptions:

| Table | Deviation | Justification |
|---|---|---|
| `sites` | Stores `suitability_score` and `risk_category` directly rather than only in a separate `predictions` table | These are the two fields queried on every single map render — denormalizing them onto `sites` avoids a join on the app's hottest read path |
| `verification_logs` | Stores computed `deviation_pct` rather than deriving it at query time | This value drives both the status flag and the frontend chart; storing it avoids recomputation and keeps historical values stable even if the deviation formula is later refined |

All other tables follow strict 3NF — no repeating groups, no transitive dependencies, every non-key column depends only on its table's primary key.

---

## 4. Full Data Dictionary & DDL

### 4.1 `regions`
Reference table defining selectable analysis regions (states/districts) and custom-drawn areas.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `region_id` | UUID | PK, default `gen_random_uuid()` | |
| `region_name` | VARCHAR(100) | NOT NULL | e.g., `"Prayagraj"` |
| `region_type` | VARCHAR(20) | CHECK IN ('state','district','custom') | |
| `state` | VARCHAR(100) | NOT NULL | Parent state, for filtering |
| `boundary_geom` | GEOMETRY(POLYGON, 4326) | NOT NULL | Region boundary, SRID 4326 (WGS 84) |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |

```sql
CREATE TABLE regions (
    region_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_name    VARCHAR(100) NOT NULL,
    region_type    VARCHAR(20) NOT NULL CHECK (region_type IN ('state','district','custom')),
    state          VARCHAR(100) NOT NULL,
    boundary_geom  GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_regions_boundary ON regions USING GIST (boundary_geom);
CREATE INDEX idx_regions_state ON regions (state);
```

---

### 4.2 `sites`
Every scored candidate recharge site.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `site_id` | UUID | PK | |
| `region_id` | UUID | FK → `regions.region_id`, NOT NULL, indexed | |
| `location` | GEOGRAPHY(POINT, 4326) | NOT NULL | Native geospatial point for distance queries |
| `suitability_score` | FLOAT | NOT NULL, CHECK (0 ≤ score ≤ 1) | |
| `risk_category` | VARCHAR(10) | CHECK IN ('Low','Medium','High'), nullable | Null until Module 4 runs |
| `model_version_id` | VARCHAR(50) | FK → `model_versions.model_version_id`, NOT NULL | Traceability |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | |

```sql
CREATE TABLE sites (
    site_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id          UUID NOT NULL REFERENCES regions(region_id),
    location           GEOGRAPHY(POINT, 4326) NOT NULL,
    suitability_score  FLOAT NOT NULL CHECK (suitability_score BETWEEN 0 AND 1),
    risk_category       VARCHAR(10) CHECK (risk_category IN ('Low','Medium','High')),
    model_version_id    VARCHAR(50) NOT NULL REFERENCES model_versions(model_version_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sites_location ON sites USING GIST (location);
CREATE INDEX idx_sites_region ON sites (region_id);
CREATE INDEX idx_sites_score ON sites (suitability_score DESC);
```

---

### 4.3 `site_features`
One-to-one raw feature values used to produce each site's score (feeds Module 2's explainability).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `site_id` | UUID | PK, FK → `sites.site_id` | 1:1 with `sites` |
| `slope_deg` | FLOAT | NOT NULL | Degrees |
| `soil_type` | VARCHAR(50) | NOT NULL | |
| `land_use` | VARCHAR(50) | NOT NULL | |
| `rainfall_mm` | FLOAT | NOT NULL | Annual/seasonal, per model design |
| `drainage_density` | FLOAT | NOT NULL | |
| `geology_type` | VARCHAR(50) | NOT NULL | |
| `depth_to_groundwater_m` | FLOAT | NULLABLE | Null if no nearby well for estimation |

```sql
CREATE TABLE site_features (
    site_id                 UUID PRIMARY KEY REFERENCES sites(site_id) ON DELETE CASCADE,
    slope_deg               FLOAT NOT NULL,
    soil_type               VARCHAR(50) NOT NULL,
    land_use                VARCHAR(50) NOT NULL,
    rainfall_mm              FLOAT NOT NULL,
    drainage_density         FLOAT NOT NULL,
    geology_type             VARCHAR(50) NOT NULL,
    depth_to_groundwater_m   FLOAT
);
```

---

### 4.4 `explanations`
Stores Module 2's SHAP-derived explanation per site.

```sql
CREATE TABLE explanations (
    explanation_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id              UUID NOT NULL REFERENCES sites(site_id) ON DELETE CASCADE,
    shap_values          JSONB NOT NULL,
    plain_text_summary   TEXT NOT NULL,
    generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (site_id)
);
CREATE INDEX idx_explanations_site ON explanations (site_id);
```
`shap_values` is stored as `JSONB` (not a fixed set of columns) because the feature set may evolve between model versions — JSONB allows schema flexibility while still being indexable/queryable if needed (`shap_values -> 'slope_deg'`).

---

### 4.5 `structures`
A site that has been confirmed as actually built.

```sql
CREATE TABLE structures (
    structure_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id          UUID NOT NULL REFERENCES sites(site_id),
    build_date        DATE NOT NULL,
    structure_type    VARCHAR(50) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','decommissioned')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (site_id)
);
CREATE INDEX idx_structures_site ON structures (site_id);
```

---

### 4.6 `wells`
Registry of groundwater monitoring wells (from CGWB/India-WRIS), used as ground truth.

```sql
CREATE TABLE wells (
    well_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id            UUID NOT NULL REFERENCES regions(region_id),
    location              GEOGRAPHY(POINT, 4326) NOT NULL,
    source                VARCHAR(30) NOT NULL CHECK (source IN ('CGWB','India-WRIS')),
    cgwb_station_code     VARCHAR(50) UNIQUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wells_location ON wells USING GIST (location);
CREATE INDEX idx_wells_region ON wells (region_id);
```

---

### 4.7 `well_readings`
Time-series of actual groundwater level observations — the system's core ground-truth data.

```sql
CREATE TABLE well_readings (
    reading_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    well_id              UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    reading_date          DATE NOT NULL,
    water_level_m         FLOAT NOT NULL,
    source_updated_at     TIMESTAMPTZ NOT NULL,
    UNIQUE (well_id, reading_date)
);
CREATE INDEX idx_well_readings_well_date ON well_readings (well_id, reading_date DESC);
```
The `UNIQUE (well_id, reading_date)` constraint is the core idempotency mechanism referenced in Rules.md Section 6 — a re-run of the daily ingestion job can safely `INSERT ... ON CONFLICT (well_id, reading_date) DO UPDATE` without ever creating duplicate rows.

---

### 4.8 `structure_wells`
Junction table linking each structure to its nearest monitoring wells (many-to-many).

```sql
CREATE TABLE structure_wells (
    structure_id    UUID NOT NULL REFERENCES structures(structure_id) ON DELETE CASCADE,
    well_id          UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    distance_m        FLOAT NOT NULL,
    PRIMARY KEY (structure_id, well_id)
);
CREATE INDEX idx_structure_wells_structure ON structure_wells (structure_id);
```

---

### 4.9 `verification_logs`
Module 3's output — one row per scheduled check per structure.

```sql
CREATE TABLE verification_logs (
    log_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    structure_id          UUID NOT NULL REFERENCES structures(structure_id) ON DELETE CASCADE,
    model_version_id       VARCHAR(50) NOT NULL REFERENCES model_versions(model_version_id),
    check_date             DATE NOT NULL,
    predicted_level_m      FLOAT NOT NULL,
    actual_level_m         FLOAT NOT NULL,
    deviation_pct           FLOAT NOT NULL,
    status                  VARCHAR(20) NOT NULL CHECK (status IN ('OK','Underperforming')),
    UNIQUE (structure_id, check_date)
);
CREATE INDEX idx_verification_structure_date ON verification_logs (structure_id, check_date DESC);
CREATE INDEX idx_verification_status ON verification_logs (status) WHERE status = 'Underperforming';
```
The partial index on `status = 'Underperforming'` is deliberate — the dashboard's most common query is "show me all currently underperforming structures," and a partial index keeps that query fast without indexing the much larger set of routine "OK" rows.

---

### 4.10 `model_versions`
Registry of every trained model artifact, for full reproducibility.

```sql
CREATE TABLE model_versions (
    model_version_id       VARCHAR(50) PRIMARY KEY,
    module_name             VARCHAR(30) NOT NULL CHECK (module_name IN ('site_recommendation','verification','risk_screening')),
    algorithm                VARCHAR(30) NOT NULL,
    trained_on               DATE NOT NULL,
    hyperparameters           JSONB NOT NULL,
    evaluation_metrics         JSONB NOT NULL,
    training_data_snapshot     VARCHAR(100) NOT NULL,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
```
Example `model_version_id` value: `"site_rec_xgb_v1.2_20270315"` — matches the file-naming convention defined in Rules.md Section 5.6.

---

### 4.11 `data_refresh_log`
Tracks every scheduled ingestion run, per Architecture.md Section 7 and Rules.md Section 2 (no silent failures).

```sql
CREATE TABLE data_refresh_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_id        UUID REFERENCES regions(region_id),
    source_name       VARCHAR(50) NOT NULL,
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    status             VARCHAR(20) NOT NULL CHECK (status IN ('success','failure','partial')),
    error_message       TEXT
);
CREATE INDEX idx_refresh_log_source_time ON data_refresh_log (source_name, fetched_at DESC);
```

---

## 5. Indexing Strategy Summary

| Index Type | Where Used | Purpose |
|---|---|---|
| GIST spatial index | `regions.boundary_geom`, `sites.location`, `wells.location` | Enables fast `ST_Contains`, `ST_DWithin` proximity/containment queries — essential for Module 4's buffer analysis and Module 3's nearest-well lookup |
| B-tree composite index | `well_readings (well_id, reading_date DESC)` | Optimizes "get latest N readings for this well" — the most frequent verification query |
| Partial index | `verification_logs (status) WHERE status = 'Underperforming'` | Keeps the dashboard's alert-list query fast without bloating the index with routine rows |
| Unique constraint (as index) | `well_readings (well_id, reading_date)` | Enforces ingestion idempotency (Section 4.7) |
| Standard B-tree | Foreign key columns (`region_id`, `site_id`, `structure_id`, etc.) | Standard join performance |

---

## 6. Common Query Patterns (Reference)

**Find all wells within 2km of a candidate site (used by Module 3):**
```sql
SELECT w.well_id, w.cgwb_station_code,
       ST_Distance(w.location, s.location) AS distance_m
FROM wells w, sites s
WHERE s.site_id = :site_id
  AND ST_DWithin(w.location, s.location, 2000)
ORDER BY distance_m
LIMIT 3;
```

**Get top 20 highest-suitability sites in a region with Low risk (used by Map Dashboard):**
```sql
SELECT site_id, ST_AsGeoJSON(location) AS geojson, suitability_score, risk_category
FROM sites
WHERE region_id = :region_id AND risk_category = 'Low'
ORDER BY suitability_score DESC
LIMIT 20;
```

**Get all currently underperforming structures across a region (used by alert view):**
```sql
SELECT st.structure_id, s.location, vl.check_date, vl.deviation_pct
FROM verification_logs vl
JOIN structures st ON st.structure_id = vl.structure_id
JOIN sites s ON s.site_id = st.site_id
WHERE s.region_id = :region_id
  AND vl.status = 'Underperforming'
  AND vl.check_date = (
      SELECT MAX(check_date) FROM verification_logs vl2 WHERE vl2.structure_id = st.structure_id
  );
```

---

## 7. Storage Estimate (Free-Tier Feasibility Check)

| Table | Est. Rows (Year 1, single state pilot) | Est. Row Size | Est. Total |
|---|---|---|---|
| `sites` | ~50,000 | ~200 bytes | ~10 MB |
| `site_features` | ~50,000 | ~150 bytes | ~7.5 MB |
| `explanations` | ~50,000 | ~1 KB (JSONB) | ~50 MB |
| `wells` | ~2,000 | ~150 bytes | ~0.3 MB |
| `well_readings` | ~2,000 wells × 365 days | ~100 bytes | ~73 MB |
| `verification_logs` | ~500 structures × 365 checks | ~150 bytes | ~27 MB |
| **Total (approx., + indexes ~2x)** | | | **~350 MB** |

This comfortably fits within any standard free-tier PostgreSQL offering (typically 1 GB minimum), confirming the schema design does not put the project's zero-cost constraint at risk even at a full single-state pilot scale.

---

## 8. Data Retention & Archival Policy

| Data Type | Retention Rule | Rationale |
|---|---|---|
| `well_readings` | Retain indefinitely | Small footprint (Section 7); full history is valuable training data for future model improvements |
| `verification_logs` | Retain indefinitely | Core evidence for the project's "did it actually work" claim — never delete |
| `data_refresh_log` | Retain 6 months, then archive/prune older entries | Operational log, not analytically valuable long-term |
| `explanations` | Retain latest per site; older explanations superseded by retraining may be archived | Keeps storage bounded as models are retrained over the project year |

---

## 9. Migration Strategy

- All schema changes are managed via **Alembic** migration scripts (per Rules.md Section 3.3) — the schema in this document represents the target state after the initial migration (`0001_initial_schema.py`).
- Every subsequent schema change ships as its own migration file, referenced by a short description matching the PR that introduces it.
- No migration is applied directly to a shared/deployed database without first running against a local copy — this is a hard rule per Rules.md Section 4 (no direct schema edits).

---

*End of Document*
