"use client";

import React, { useCallback } from "react";
import dynamic from "next/dynamic";
import { useMapStore } from "@/store/map-store";
import {
  RegionFeature,
  WellFeature,
  RecommendationFeature,
  StructureFeature,
} from "@/lib/types";

import { WellPopup } from "./popups/WellPopup";
import { RecommendationPopup } from "./popups/RecommendationPopup";
import { StructurePopup } from "./popups/StructurePopup";

const DeckGLMap = dynamic(() => import("./DeckGLMap").then((m) => m.DeckGLMap), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-slate-950 flex items-center justify-center text-slate-400">Loading GPU Engine...</div>,
});

const LeafletMap = dynamic(() => import("./LeafletMap").then((m) => m.LeafletMap), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-slate-950 flex items-center justify-center text-slate-400">Loading CPU Engine...</div>,
});

interface Props {
  regions?: RegionFeature[];
  wells?: WellFeature[];
  recommendations?: RecommendationFeature[];
  structures?: StructureFeature[];
}

export const MapContainerWrapper: React.FC<Props> = ({
  regions = [],
  wells = [],
  recommendations = [],
  structures = [],
}) => {
  const { renderEngine, selectedFeature, setSelectedFeature } = useMapStore();

  const handleSelectFeature = useCallback(
    (type: "well" | "recommendation" | "structure", feature: any) => {
      setSelectedFeature({ type, data: feature });
    },
    [setSelectedFeature]
  );

  return (
    <div className="w-full h-full relative overflow-hidden">
      {renderEngine === "deckgl" ? (
        <DeckGLMap
          regions={regions}
          wells={wells}
          recommendations={recommendations}
          structures={structures}
          onSelectFeature={handleSelectFeature}
        />
      ) : (
        <LeafletMap
          regions={regions}
          wells={wells}
          recommendations={recommendations}
          structures={structures}
          onSelectFeature={handleSelectFeature}
        />
      )}

      {/* Floating Popup Modal overlay */}
      {selectedFeature && (
        <div className="absolute top-5 right-5 z-[2000]">
          {selectedFeature.type === "well" && (
            <WellPopup
              feature={selectedFeature.data}
              onClose={() => setSelectedFeature(null)}
            />
          )}
          {selectedFeature.type === "recommendation" && (
            <RecommendationPopup
              feature={selectedFeature.data}
              onClose={() => setSelectedFeature(null)}
            />
          )}
          {selectedFeature.type === "structure" && (
            <StructurePopup
              feature={selectedFeature.data}
              onClose={() => setSelectedFeature(null)}
            />
          )}
        </div>
      )}
    </div>
  );
};
