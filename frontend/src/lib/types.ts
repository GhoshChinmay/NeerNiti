export interface RegionFeature {
  type: "Feature";
  geometry: {
    type: string;
    coordinates: any;
  };
  properties: {
    region_id: string;
    region_name: string;
    region_type: "state" | "district" | "custom";
    state: string;
  };
}

export interface WellReadingHistory {
  date: string;
  water_level_m: number;
}

export interface WellFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    well_id: string;
    station_code: string | null;
    source: "CGWB" | "India-WRIS";
    latest_water_level_m: number | null;
    reading_date: string | null;
    reading_history: WellReadingHistory[];
  };
}

export interface SubScores {
  slope_score: number;
  ndvi_score: number;
  water_level_score: number;
}

export interface RecommendationFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    recommendation_id: string;
    final_suitability_score: number;
    structure_type: string;
    risk_category: "Low" | "Medium" | "High";
    explanation_text: string;
    sub_scores: SubScores;
    created_at: string | null;
  };
}

export interface VerificationLog {
  date: string;
  predicted_m: number;
  actual_m: number;
  deviation_pct: number;
  status: "OK" | "Underperforming" | "Critical";
}

export interface StructureFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    structure_id: string;
    structure_type: "Check Dam" | "Percolation Tank" | "Recharge Well" | "Farm Pond";
    construction_date: string | null;
    current_status: "Active" | "Inactive" | "Under Construction" | "Underperforming" | "OK";
    verification_logs: VerificationLog[];
  };
}

export interface GeoJSONCollection<T> {
  type: "FeatureCollection";
  features: T[];
}

export interface ModelVersion {
  model_version_id: string;
  module_name: "site_recommendation" | "verification" | "risk_screening";
  algorithm: string;
  trained_on: string;
  hyperparameters: Record<string, any>;
  evaluation_metrics: Record<string, any>;
  training_data_snapshot: string;
  created_at: string;
}

export interface DataRefreshLog {
  log_id: string;
  region_id: string | null;
  source_name: string;
  fetched_at: string;
  status: "success" | "failure" | "partial";
  error_message: string | null;
}
