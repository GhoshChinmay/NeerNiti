"use client";

import React from "react";
import { RecommendationFeature } from "@/lib/types";
import { useMapStore } from "@/store/map-store";
import { Award, X, Sparkles, ChevronRight, Hammer } from "lucide-react";

interface Props {
  feature: RecommendationFeature;
  onClose: () => void;
}

export const RecommendationPopup: React.FC<Props> = ({ feature, onClose }) => {
  const { openSiteDetail, openMarkAsBuiltModal } = useMapStore();
  const props = feature.properties;

  const riskBadgeColor =
    props.risk_category === "High"
      ? "bg-red-500/20 text-red-400 border-red-500/30"
      : props.risk_category === "Medium"
      ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
      : "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";

  return (
    <div className="w-80 bg-slate-900/95 text-slate-100 p-4 rounded-2xl border border-slate-700/80 shadow-2xl backdrop-blur-xl relative font-sans text-xs">
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-slate-400 hover:text-white p-1 rounded-lg transition-colors cursor-pointer"
      >
        <X size={14} />
      </button>

      <div className="flex items-center gap-2 mb-2 pr-6">
        <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
          <Award size={16} />
        </div>
        <div>
          <h3 className="font-bold text-sm text-amber-400">AI Recommended Site</h3>
          <p className="text-[10px] text-slate-400">{props.structure_type}</p>
        </div>
      </div>

      <div className="flex items-center justify-between bg-slate-800/80 p-3 rounded-xl border border-slate-700/50 mb-3">
        <div>
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">Suitability Score</div>
          <div className="text-xl font-extrabold text-amber-400 font-mono">
            {(props.final_suitability_score / 100).toFixed(2)}{" "}
            <span className="text-xs text-slate-400 font-normal">/ 1.00</span>
          </div>
        </div>
        <div className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${riskBadgeColor}`}>
          {props.risk_category || "Low"} Risk
        </div>
      </div>

      <div className="space-y-1 mb-3 bg-slate-800/40 p-2.5 rounded-xl border border-slate-700/40">
        <div className="flex items-center gap-1.5 text-amber-300 font-medium text-[11px]">
          <Sparkles size={13} /> Explanation
        </div>
        <p className="text-slate-300 italic leading-relaxed text-[11px] border-l-2 border-amber-500 pl-2">
          &ldquo;{props.explanation_text}&rdquo;
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => openSiteDetail(feature)}
          className="flex-1 py-1.5 px-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold flex items-center justify-center gap-1 transition-colors cursor-pointer"
        >
          <span>Detail Panel</span>
          <ChevronRight size={13} />
        </button>

        <button
          onClick={() => openMarkAsBuiltModal(feature)}
          className="py-1.5 px-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-[11px] font-extrabold flex items-center gap-1 shadow-md transition-colors cursor-pointer"
        >
          <Hammer size={12} />
          <span>Build</span>
        </button>
      </div>
    </div>
  );
};
