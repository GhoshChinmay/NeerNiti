"use client";

import React from "react";
import { Droplet, Award, Hammer, AlertTriangle, ShieldCheck } from "lucide-react";
import {
  WellFeature,
  RecommendationFeature,
  StructureFeature,
} from "@/lib/types";

interface Props {
  wells?: WellFeature[];
  recommendations?: RecommendationFeature[];
  structures?: StructureFeature[];
}

export const StatsCards: React.FC<Props> = ({
  wells = [],
  recommendations = [],
  structures = [],
}) => {
  const totalWells = wells.length;
  const totalRecommendations = recommendations.length;
  const totalStructures = structures.length;

  const underperformingCount = structures.filter(
    (s) => s.properties.current_status === "Underperforming"
  ).length;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Wells Card */}
      <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3.5 py-2 rounded-xl shadow-lg">
        <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
          <Droplet size={18} />
        </div>
        <div>
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Wells</div>
          <div className="text-base font-extrabold text-slate-100">{totalWells}</div>
        </div>
      </div>

      {/* Recommendations Card */}
      <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3.5 py-2 rounded-xl shadow-lg">
        <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
          <Award size={18} />
        </div>
        <div>
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Recommendations</div>
          <div className="text-base font-extrabold text-amber-400">{totalRecommendations}</div>
        </div>
      </div>

      {/* Built Structures Card */}
      <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3.5 py-2 rounded-xl shadow-lg">
        <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
          <Hammer size={18} />
        </div>
        <div>
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Built Structures</div>
          <div className="text-base font-extrabold text-cyan-400">{totalStructures}</div>
        </div>
      </div>

      {/* Verification Status Alert Card */}
      <div className="flex items-center gap-3 bg-slate-900/80 backdrop-blur-md border border-slate-800 px-3.5 py-2 rounded-xl shadow-lg">
        <div
          className={`p-2 rounded-lg ${
            underperformingCount > 0
              ? "bg-red-500/20 text-red-400 border border-red-500/30"
              : "bg-emerald-500/20 text-emerald-400"
          }`}
        >
          {underperformingCount > 0 ? <AlertTriangle size={18} /> : <ShieldCheck size={18} />}
        </div>
        <div>
          <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Bi-LSTM Alert Status</div>
          <div
            className={`text-base font-extrabold ${
              underperformingCount > 0 ? "text-red-400" : "text-emerald-400"
            }`}
          >
            {underperformingCount > 0 ? `${underperformingCount} Underperforming` : "All Systems OK"}
          </div>
        </div>
      </div>
    </div>
  );
};
