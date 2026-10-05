"use client";

import React, { useMemo, useState, useCallback } from "react";
import DeckGL from "@deck.gl/react";
import { GeoJsonLayer, ScatterplotLayer } from "@deck.gl/layers";
import Map from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";

import { useMapStore } from "@/store/map-store";
import {
  RegionFeature,
  WellFeature,
  RecommendationFeature,
  StructureFeature,
} from "@/lib/types";

interface Props {
  regions?: RegionFeature[];
  wells?: WellFeature[];
  recommendations?: RecommendationFeature[];
  structures?: StructureFeature[];
  onSelectFeature: (type: "well" | "recommendation" | "structure", feature: any) => void;
}

export const DeckGLMap: React.FC<Props> = ({
  regions = [],
  wells = [],
  recommendations = [],
  structures = [],
  onSelectFeature,
}) => {
  const {
    latitude,
    longitude,
    zoom,
    setViewport,
    showRegions,
    showWells,
    showRecommendations,
    showStructures,
    riskFilter,
    minSuitabilityScore,
    lowPerformanceMode,
  } = useMapStore();

  const [viewState, setViewState] = useState({
    latitude,
    longitude,
    zoom,
    pitch: 0,
    bearing: 0,
  });

  const onViewStateChange = useCallback(
    ({ viewState }: any) => {
      setViewState(viewState);
      setViewport(viewState.latitude, viewState.longitude, viewState.zoom);
    },
    [setViewport]
  );

  // Filter recommendations
  const filteredRecommendations = useMemo(() => {
    return recommendations.filter((r) => {
      const props = r.properties;
      if (props.final_suitability_score < minSuitabilityScore) return false;
      if (riskFilter !== "All" && props.risk_category !== riskFilter) return false;
      return true;
    });
  }, [recommendations, minSuitabilityScore, riskFilter]);

  // Handle WebGL Context Initialization
  const handleWebGLInitialized = useCallback(() => {
    console.info("WebGL context initialized successfully.");
  }, []);

  // Deck.gl layers setup
  const layers = useMemo(() => {
    const layerList: any[] = [];

    // Regions Layer (Polygons)
    if (showRegions && regions.length > 0) {
      layerList.push(
        new GeoJsonLayer({
          id: "regions-layer",
          data: regions as any,
          filled: true,
          stroked: true,
          getFillColor: [76, 175, 80, 20],
          getLineColor: [76, 175, 80, 150],
          getLineWidth: 2,
          lineWidthMinPixels: 1,
          pickable: true,
        })
      );
    }

    // Wells Layer (Blue Dots)
    if (showWells && wells.length > 0) {
      layerList.push(
        new ScatterplotLayer({
          id: "wells-layer",
          data: wells as any,
          getPosition: (d: any) => d.geometry.coordinates,
          getFillColor: [33, 150, 243, 220],
          getLineColor: [255, 255, 255, 255],
          getRadius: lowPerformanceMode ? 300 : 400,
          radiusMinPixels: 5,
          radiusMaxPixels: 12,
          lineWidthMinPixels: 1,
          stroked: true,
          pickable: true,
          onClick: ({ object }: any) => {
            if (object) onSelectFeature("well", object);
          },
        })
      );
    }

    // AI Recommendations Layer (Gold Glowing Dots)
    if (showRecommendations && filteredRecommendations.length > 0) {
      layerList.push(
        new ScatterplotLayer({
          id: "recommendations-layer",
          data: filteredRecommendations as any,
          getPosition: (d: any) => d.geometry.coordinates,
          getFillColor: (d: any) => {
            const risk = d.properties.risk_category;
            if (risk === "High") return [244, 67, 54, 230];
            if (risk === "Medium") return [255, 179, 0, 230];
            return [255, 193, 7, 230];
          },
          getLineColor: [255, 255, 255, 255],
          getRadius: 600,
          radiusMinPixels: 8,
          radiusMaxPixels: 16,
          lineWidthMinPixels: 2,
          stroked: true,
          pickable: true,
          onClick: ({ object }: any) => {
            if (object) onSelectFeature("recommendation", object);
          },
        })
      );
    }

    // Built Structures Layer (Cyan / Red Dots)
    if (showStructures && structures.length > 0) {
      layerList.push(
        new ScatterplotLayer({
          id: "structures-layer",
          data: structures as any,
          getPosition: (d: any) => d.geometry.coordinates,
          getFillColor: (d: any) => {
            return d.properties.current_status === "Underperforming"
              ? [244, 67, 54, 240]
              : [0, 188, 212, 240];
          },
          getLineColor: [255, 255, 255, 255],
          getRadius: 600,
          radiusMinPixels: 8,
          radiusMaxPixels: 16,
          lineWidthMinPixels: 2,
          stroked: true,
          pickable: true,
          onClick: ({ object }: any) => {
            if (object) onSelectFeature("structure", object);
          },
        })
      );
    }

    return layerList;
  }, [
    showRegions,
    showWells,
    showRecommendations,
    showStructures,
    regions,
    wells,
    filteredRecommendations,
    structures,
    lowPerformanceMode,
    onSelectFeature,
  ]);

  return (
    <div className="w-full h-full relative">
      <DeckGL
        viewState={viewState}
        onViewStateChange={onViewStateChange}
        controller={true}
        layers={layers}
        useDevicePixels={lowPerformanceMode ? false : true}
        onWebGLInitialized={handleWebGLInitialized}
      >
        <Map
          mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
          failIfMajorPerformanceCaveat={false}
          preserveDrawingBuffer={false}
        />
      </DeckGL>
    </div>
  );
};
