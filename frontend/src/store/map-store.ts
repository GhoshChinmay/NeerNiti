import { create } from "zustand";
import { RecommendationFeature, StructureFeature } from "@/lib/types";

export type RenderEngine = "deckgl" | "leaflet";

export interface MapState {
  // Viewport
  latitude: number;
  longitude: number;
  zoom: number;
  setViewport: (lat: number, lng: number, zoom: number) => void;

  // Selected Region
  selectedRegionId: string | null;
  selectedDistrictName: string;
  setSelectedRegion: (regionId: string | null, districtName: string) => void;

  // Layer visibility toggles
  showRegions: boolean;
  showWells: boolean;
  showRecommendations: boolean;
  showStructures: boolean;
  toggleLayer: (layer: "showRegions" | "showWells" | "showRecommendations" | "showStructures") => void;

  // Render mode (CPU / WebGL settings)
  renderEngine: RenderEngine;
  setRenderEngine: (engine: RenderEngine) => void;
  lowPerformanceMode: boolean;
  setLowPerformanceMode: (enabled: boolean) => void;

  // Filter state
  riskFilter: "All" | "Low" | "Medium" | "High";
  setRiskFilter: (risk: "All" | "Low" | "Medium" | "High") => void;
  minSuitabilityScore: number;
  setMinSuitabilityScore: (score: number) => void;

  // Selected feature for inspector / modal / popup
  selectedFeature: {
    type: "well" | "recommendation" | "structure";
    data: any;
  } | null;
  setSelectedFeature: (feature: { type: "well" | "recommendation" | "structure"; data: any } | null) => void;

  // Site Detail Panel overlay
  siteDetailOpen: boolean;
  selectedSite: RecommendationFeature | null;
  openSiteDetail: (site: RecommendationFeature) => void;
  closeSiteDetail: () => void;

  // "Mark as Built" Modal state
  markAsBuiltSite: RecommendationFeature | null;
  openMarkAsBuiltModal: (site: RecommendationFeature) => void;
  closeMarkAsBuiltModal: () => void;

  // Data Freshness Modal
  dataFreshnessOpen: boolean;
  setDataFreshnessOpen: (open: boolean) => void;

  // FAQ Modal
  faqOpen: boolean;
  setFaqOpen: (open: boolean) => void;

  // UI Sidebar toggle
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  // Real-time status alerts count
  alertCount: number;
  incrementAlertCount: () => void;
}

export const useMapStore = create<MapState>((set) => ({
  latitude: 25.4358,
  longitude: 81.8463,
  zoom: 10,
  setViewport: (latitude, longitude, zoom) => set({ latitude, longitude, zoom }),

  selectedRegionId: null,
  selectedDistrictName: "Prayagraj",
  setSelectedRegion: (selectedRegionId, selectedDistrictName) =>
    set({
      selectedRegionId,
      selectedDistrictName,
      latitude: selectedDistrictName === "Mirzapur" ? 25.1337 : 25.4358,
      longitude: selectedDistrictName === "Mirzapur" ? 82.5644 : 81.8463,
      zoom: 10,
    }),

  showRegions: true,
  showWells: true,
  showRecommendations: true,
  showStructures: true,
  toggleLayer: (layer) => set((state) => ({ [layer]: !state[layer] })),

  renderEngine: "deckgl",
  setRenderEngine: (renderEngine) => set({ renderEngine }),
  lowPerformanceMode: false,
  setLowPerformanceMode: (lowPerformanceMode) => set({ lowPerformanceMode }),

  riskFilter: "All",
  setRiskFilter: (riskFilter) => set({ riskFilter }),
  minSuitabilityScore: 60,
  setMinSuitabilityScore: (minSuitabilityScore) => set({ minSuitabilityScore: Math.max(60, minSuitabilityScore) }),

  selectedFeature: null,
  setSelectedFeature: (selectedFeature) => set({ selectedFeature }),

  siteDetailOpen: false,
  selectedSite: null,
  openSiteDetail: (site) => set({ siteDetailOpen: true, selectedSite: site, selectedFeature: { type: "recommendation", data: site } }),
  closeSiteDetail: () => set({ siteDetailOpen: false, selectedSite: null }),

  markAsBuiltSite: null,
  openMarkAsBuiltModal: (site) => set({ markAsBuiltSite: site }),
  closeMarkAsBuiltModal: () => set({ markAsBuiltSite: null }),

  dataFreshnessOpen: false,
  setDataFreshnessOpen: (open) => set({ dataFreshnessOpen: open }),

  faqOpen: false,
  setFaqOpen: (open) => set({ faqOpen: open }),

  sidebarOpen: true,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen: typeof sidebarOpen === "boolean" ? sidebarOpen : !sidebarOpen }),

  alertCount: 0,
  incrementAlertCount: () => set((state) => ({ alertCount: state.alertCount + 1 })),
}));
