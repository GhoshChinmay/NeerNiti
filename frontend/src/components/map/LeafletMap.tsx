"use client";

import React, { useMemo } from "react";
import { useMapStore } from "@/store/map-store";
import {
  RegionFeature,
  WellFeature,
  RecommendationFeature,
  StructureFeature,
} from "@/lib/types";

// Dynamically imported React Leaflet components to avoid SSR window errors
import { MapContainer as ReactLeafletMap, TileLayer, GeoJSON, CircleMarker } from "react-leaflet";
import "leaflet/dist/leaflet.css";

interface Props {
  regions?: RegionFeature[];
  wells?: WellFeature[];
  recommendations?: RecommendationFeature[];
  structures?: StructureFeature[];
  onSelectFeature: (type: "well" | "recommendation" | "structure", feature: any) => void;
}

export const LeafletMap: React.FC<Props> = ({
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
    showRegions,
    showWells,
    showRecommendations,
    showStructures,
    riskFilter,
    minSuitabilityScore,
  } = useMapStore();

  const filteredRecommendations = useMemo(() => {
    return recommendations.filter((r) => {
      const props = r.properties;
      if (props.final_suitability_score < minSuitabilityScore) return false;
      if (riskFilter !== "All" && props.risk_category !== riskFilter) return false;
      return true;
    });
  }, [recommendations, minSuitabilityScore, riskFilter]);

  return (
    <div className="w-full h-full relative">
      <ReactLeafletMap
        center={[latitude, longitude]}
        zoom={zoom}
        style={{ width: "100%", height: "100%" }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={20}
        />

        {showRegions && regions.length > 0 && (
          <GeoJSON
            key={JSON.stringify(regions.length)}
            data={{
              type: "FeatureCollection",
              features: regions,
            } as any}
            style={{
              color: "#4CAF50",
              weight: 2,
              opacity: 0.6,
              fillOpacity: 0.05,
            }}
          />
        )}

        {showWells &&
          wells.map((well) => (
            <CircleMarker
              key={well.properties.well_id}
              center={[well.geometry.coordinates[1], well.geometry.coordinates[0]]}
              radius={6}
              pathOptions={{
                fillColor: "#2196F3",
                color: "#ffffff",
                weight: 1,
                fillOpacity: 0.8,
              }}
              eventHandlers={{
                click: () => onSelectFeature("well", well),
              }}
            />
          ))}

        {showRecommendations &&
          filteredRecommendations.map((rec) => {
            const risk = rec.properties.risk_category;
            const color = risk === "High" ? "#F44336" : risk === "Medium" ? "#FFB300" : "#FFC107";
            return (
              <CircleMarker
                key={rec.properties.recommendation_id}
                center={[rec.geometry.coordinates[1], rec.geometry.coordinates[0]]}
                radius={10}
                pathOptions={{
                  fillColor: color,
                  color: "#FFA000",
                  weight: 2,
                  fillOpacity: 0.9,
                }}
                eventHandlers={{
                  click: () => onSelectFeature("recommendation", rec),
                }}
              />
            );
          })}

        {showStructures &&
          structures.map((struct) => {
            const isWarn = struct.properties.current_status === "Underperforming";
            const color = isWarn ? "#F44336" : "#00BCD4";
            return (
              <CircleMarker
                key={struct.properties.structure_id}
                center={[struct.geometry.coordinates[1], struct.geometry.coordinates[0]]}
                radius={10}
                pathOptions={{
                  fillColor: color,
                  color: "#ffffff",
                  weight: 2,
                  fillOpacity: 0.9,
                }}
                eventHandlers={{
                  click: () => onSelectFeature("structure", struct),
                }}
              />
            );
          })}
      </ReactLeafletMap>
    </div>
  );
};
