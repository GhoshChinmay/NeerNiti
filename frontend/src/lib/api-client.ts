import {
  RegionsSchema,
  WellsSchema,
  RecommendationsSchema,
  StructuresSchema,
} from "./schemas";
import {
  GeoJSONCollection,
  RegionFeature,
  WellFeature,
  RecommendationFeature,
  StructureFeature,
  ModelVersion,
  DataRefreshLog,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";

export async function fetchRegions(): Promise<GeoJSONCollection<RegionFeature>> {
  const res = await fetch(`${API_BASE}/regions`);
  if (!res.ok) {
    throw new Error(`Failed to fetch regions: ${res.statusText}`);
  }
  const json = await res.json();
  return RegionsSchema.parse(json) as GeoJSONCollection<RegionFeature>;
}

export async function fetchWells(): Promise<GeoJSONCollection<WellFeature>> {
  const res = await fetch(`${API_BASE}/wells`);
  if (!res.ok) {
    throw new Error(`Failed to fetch wells: ${res.statusText}`);
  }
  const json = await res.json();
  return WellsSchema.parse(json) as GeoJSONCollection<WellFeature>;
}

export async function fetchRecommendations(params?: {
  region_id?: string;
  min_score?: number;
  risk?: string;
  limit?: number;
}): Promise<GeoJSONCollection<RecommendationFeature>> {
  const query = new URLSearchParams();
  if (params?.region_id) query.set("region_id", params.region_id);
  if (params?.min_score) query.set("min_score", String(params.min_score));
  if (params?.risk) query.set("risk", params.risk);
  if (params?.limit) query.set("limit", String(params.limit));

  const url = `${API_BASE}/recommendations?${query.toString()}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch recommendations: ${res.statusText}`);
  }
  const json = await res.json();
  return RecommendationsSchema.parse(json) as GeoJSONCollection<RecommendationFeature>;
}

export async function fetchStructures(): Promise<GeoJSONCollection<StructureFeature>> {
  const res = await fetch(`${API_BASE}/structures`);
  if (!res.ok) {
    throw new Error(`Failed to fetch structures: ${res.statusText}`);
  }
  const json = await res.json();
  return StructuresSchema.parse(json) as GeoJSONCollection<StructureFeature>;
}

export async function createStructure(payload: {
  site_id: string;
  structure_type: string;
  build_date?: string;
  status?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/structures`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create structure");
  }
  return res.json();
}

export async function fetchSiteDetail(site_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/sites/${site_id}`);
  if (!res.ok) throw new Error(`Failed to fetch site: ${res.statusText}`);
  return res.json();
}

export async function fetchSiteExplanation(site_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/sites/${site_id}/explanation`);
  if (!res.ok) throw new Error(`Failed to fetch explanation: ${res.statusText}`);
  return res.json();
}

export async function fetchStructureVerification(structure_id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/structures/${structure_id}/verification`);
  if (!res.ok) throw new Error(`Failed to fetch verification: ${res.statusText}`);
  return res.json();
}

export async function fetchDataRefreshStatus(): Promise<{
  data: {
    sources: Array<{
      source_name: string;
      last_fetched_at: string;
      status: string;
      message?: string;
    }>;
    system_healthy: boolean;
  };
}> {
  const res = await fetch(`${API_BASE}/data-refresh/status`);
  if (!res.ok) throw new Error(`Failed to fetch refresh status: ${res.statusText}`);
  return res.json();
}

export async function fetchModelVersions(): Promise<ModelVersion[]> {
  const res = await fetch(`${API_BASE}/admin/models`);
  if (!res.ok) {
    throw new Error(`Failed to fetch model versions: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRefreshLogs(): Promise<DataRefreshLog[]> {
  const res = await fetch(`${API_BASE}/admin/refresh-logs`);
  if (!res.ok) {
    throw new Error(`Failed to fetch refresh logs: ${res.statusText}`);
  }
  return res.json();
}
