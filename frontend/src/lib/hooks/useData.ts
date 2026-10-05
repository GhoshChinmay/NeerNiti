import { useQuery } from "@tanstack/react-query";
import {
  fetchRegions,
  fetchWells,
  fetchRecommendations,
  fetchStructures,
  fetchModelVersions,
  fetchRefreshLogs,
} from "../api-client";

export function useRegions() {
  return useQuery({
    queryKey: ["regions"],
    queryFn: fetchRegions,
    staleTime: 1000 * 60 * 15, // 15 mins
  });
}

export function useWells() {
  return useQuery({
    queryKey: ["wells"],
    queryFn: fetchWells,
    staleTime: 1000 * 60 * 5, // 5 mins
  });
}

export function useRecommendations(params?: {
  region_id?: string;
  min_score?: number;
  risk?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["recommendations", params],
    queryFn: () => fetchRecommendations(params),
    staleTime: 1000 * 60 * 5,
  });
}

export function useStructures() {
  return useQuery({
    queryKey: ["structures"],
    queryFn: fetchStructures,
    staleTime: 1000 * 60 * 5,
  });
}

export function useModelVersions() {
  return useQuery({
    queryKey: ["admin", "models"],
    queryFn: fetchModelVersions,
    staleTime: 1000 * 60 * 10,
  });
}

export function useRefreshLogs() {
  return useQuery({
    queryKey: ["admin", "refresh-logs"],
    queryFn: fetchRefreshLogs,
    staleTime: 1000 * 60 * 5,
  });
}
