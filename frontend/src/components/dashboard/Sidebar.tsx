"use client";

import React from "react";
import { useMapStore } from "@/store/map-store";
import { RecommendationFeature } from "@/lib/types";
import {
  Layers,
  Cpu,
  Zap,
  Filter,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  ListFilter,
  CheckCircle2,
  Droplet,
  Landmark,
} from "lucide-react";

interface SidebarProps {
  recommendations?: RecommendationFeature[];
}

export const Sidebar: React.FC<SidebarProps> = ({ recommendations = [] }) => {
  const {
    showRegions,
    showWells,
    showRecommendations,
    showStructures,
    toggleLayer,
    renderEngine,
    setRenderEngine,
    riskFilter,
    setRiskFilter,
    minSuitabilityScore,
    setMinSuitabilityScore,
    sidebarOpen,
    setSidebarOpen,
    openSiteDetail,
    setDataFreshnessOpen,
    setViewport,
  } = useMapStore();

  // Enforce score >= minSuitabilityScore (which is locked at >= 60 / 0.60)
  const filteredRecs = recommendations.filter((r) => {
    const score = r.properties.final_suitability_score;
    const risk = r.properties.risk_category || "Low";
    const matchesScore = score >= minSuitabilityScore;
    const matchesRisk = riskFilter === "All" || risk === riskFilter;
    return matchesScore && matchesRisk;
  });

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case "High":
        return <ShieldAlert size={12} className="text-red-400" />;
      case "Medium":
        return <AlertTriangle size={12} className="text-amber-400" />;
      default:
        return <ShieldCheck size={12} className="text-emerald-400" />;
    }
  };

  const handleSelectSiteCard = (site: RecommendationFeature) => {
    const coords = site.geometry.coordinates;
    setViewport(coords[1], coords[0], 13);
    openSiteDetail(site);
  };

  return (
    <aside
      className={`fixed top-0 left-0 h-full z-[1500] transition-all duration-300 flex select-none ${
        sidebarOpen ? "w-84" : "w-14"
      }`}
    >
      {/* Government Portal Sidebar Panel */}
      <div className="w-full h-full bg-slate-900 text-slate-100 border-r border-slate-800 flex flex-col shadow-xl overflow-hidden font-sans">
        
        {/* National Tricolor Civic Accent Strip */}
        <div className="w-full h-1 flex flex-row">
          <div className="flex-1 bg-[#FF9933]"></div>
          <div className="flex-1 bg-[#FFFFFF]"></div>
          <div className="flex-1 bg-[#138808]"></div>
        </div>

        {/* Institutional Header */}
        <div className="p-3.5 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between min-h-[64px]">
          {sidebarOpen ? (
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-900/60 border border-blue-700 flex items-center justify-center text-blue-300 font-bold shadow-sm">
                <Droplet size={18} className="text-blue-400 fill-blue-400/20" />
              </div>
              <div>
                <div className="text-[9px] uppercase tracking-wider font-extrabold text-blue-400 leading-none">
                  Govt of India • Jal Shakti
                </div>
                <h1 className="font-black text-sm text-white tracking-tight leading-tight mt-0.5">
                  NeerNiti <span className="text-amber-400 font-serif font-normal text-xs">(नीर नीति)</span>
                </h1>
                <p className="text-[9.5px] text-slate-400 font-medium leading-none mt-0.5">
                  National MAR Decision Portal
                </p>
              </div>
            </div>
          ) : (
            <div className="w-8 h-8 rounded-lg bg-blue-900/60 border border-blue-700 flex items-center justify-center text-blue-300 font-bold mx-auto">
              <Droplet size={18} className="text-blue-400" />
            </div>
          )}

          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer border border-slate-700/60"
            title={sidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
          >
            {sidebarOpen ? <ChevronLeft size={15} /> : <ChevronRight size={15} />}
          </button>
        </div>

        {/* Scrollable Body */}
        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto p-3.5 space-y-4 scrollbar-thin scrollbar-thumb-slate-800 text-xs">
            
            {/* 1. Rendering Engine Segmented Control */}
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu size={12} className="text-blue-400" /> Rendering Engine
              </div>
              <div className="grid grid-cols-2 gap-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setRenderEngine("deckgl")}
                  className={`py-1.5 px-2 rounded-md text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                    renderEngine === "deckgl"
                      ? "bg-blue-600 text-white shadow-sm font-extrabold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Zap size={12} /> GPU (Deck.gl)
                </button>
                <button
                  onClick={() => setRenderEngine("leaflet")}
                  className={`py-1.5 px-2 rounded-md text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                    renderEngine === "leaflet"
                      ? "bg-blue-600 text-white shadow-sm font-extrabold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Cpu size={12} /> CPU (Leaflet)
                </button>
              </div>
            </div>

            {/* 2. Official Thematic Map Layers */}
            <div className="space-y-2">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Layers size={12} className="text-emerald-400" /> Map Layers
              </div>

              <div className="space-y-1.5">
                {/* District Boundaries */}
                <button
                  onClick={() => toggleLayer("showRegions")}
                  className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] font-semibold hover:bg-slate-800/80 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-400"></span>
                    <span className="text-slate-200">District Boundaries</span>
                  </div>
                  {showRegions ? <Eye size={14} className="text-emerald-400" /> : <EyeOff size={14} className="text-slate-500" />}
                </button>

                {/* Monitoring Wells */}
                <button
                  onClick={() => toggleLayer("showWells")}
                  className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] font-semibold hover:bg-slate-800/80 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500 border border-blue-400"></span>
                    <span className="text-slate-200">Monitoring Wells (CGWB)</span>
                  </div>
                  {showWells ? <Eye size={14} className="text-blue-400" /> : <EyeOff size={14} className="text-slate-500" />}
                </button>

                {/* AI Recommendations */}
                <button
                  onClick={() => toggleLayer("showRecommendations")}
                  className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] font-semibold hover:bg-slate-800/80 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400 border border-amber-300"></span>
                    <span className="text-slate-200">AI Recommendations (&gt;0.60)</span>
                  </div>
                  {showRecommendations ? <Eye size={14} className="text-amber-400" /> : <EyeOff size={14} className="text-slate-500" />}
                </button>

                {/* Built Structures */}
                <button
                  onClick={() => toggleLayer("showStructures")}
                  className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-[11px] font-semibold hover:bg-slate-800/80 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 border border-cyan-300"></span>
                    <span className="text-slate-200">Built Structures (Jal Shakti)</span>
                  </div>
                  {showStructures ? <Eye size={14} className="text-cyan-400" /> : <EyeOff size={14} className="text-slate-500" />}
                </button>
              </div>
            </div>

            {/* 3. Administrative Policy & Risk Filters */}
            <div className="space-y-2.5 border-t border-slate-800 pt-3">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Filter size={12} className="text-amber-400" /> Filters &amp; Thresholds
              </div>

              {/* Contamination Risk Filter */}
              <div className="space-y-1">
                <label className="text-[11px] text-slate-300 font-semibold">Contamination Risk</label>
                <div className="grid grid-cols-4 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                  {(["All", "Low", "Medium", "High"] as const).map((risk) => (
                    <button
                      key={risk}
                      onClick={() => setRiskFilter(risk)}
                      className={`py-1 rounded text-[10px] font-bold transition-all cursor-pointer ${
                        riskFilter === risk
                          ? "bg-slate-800 text-amber-400 border border-amber-500/40 shadow-sm"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {risk}
                    </button>
                  ))}
                </div>
              </div>

              {/* Min Suitability Score Slider (Locked >= 0.60) */}
              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between items-center text-[11px] font-semibold">
                  <span className="text-slate-300">Min Suitability Score</span>
                  <span className="text-amber-400 font-bold font-mono px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800">
                    {(minSuitabilityScore / 100).toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="100"
                  step="1"
                  value={minSuitabilityScore}
                  onChange={(e) => setMinSuitabilityScore(Number(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[9px] text-slate-400 font-mono">
                  <span>0.60 (Policy Min)</span>
                  <span>1.00 (Optimal)</span>
                </div>
              </div>
            </div>

            {/* 4. Prioritized Candidate Sites List */}
            <div className="space-y-2 border-t border-slate-800 pt-3">
              <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <span className="flex items-center gap-1.5">
                  <ListFilter size={12} className="text-blue-400" /> Recommended Sites ({filteredRecs.length})
                </span>
                <span className="text-[9px] text-emerald-400 font-mono font-normal">Score &gt; 0.60</span>
              </div>

              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-800">
                {filteredRecs.length === 0 ? (
                  <div className="p-3 text-center text-[11px] text-slate-500 bg-slate-950/60 rounded-lg border border-slate-800">
                    No candidate sites found with suitability &gt; {(minSuitabilityScore / 100).toFixed(2)} in this region.
                  </div>
                ) : (
                  filteredRecs.slice(0, 15).map((rec) => {
                    const p = rec.properties;
                    return (
                      <div
                        key={p.recommendation_id}
                        onClick={() => handleSelectSiteCard(rec)}
                        className="p-2.5 bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800 hover:border-blue-500/50 rounded-lg text-xs space-y-1 transition-all cursor-pointer"
                      >
                        <div className="flex justify-between items-center">
                          <span className="font-extrabold text-slate-200">
                            Site #{p.recommendation_id.slice(0, 6)}
                          </span>
                          <span className="font-mono font-bold text-amber-400 text-xs">
                            {(p.final_suitability_score / 100).toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-slate-400">
                          <span className="font-medium text-slate-300">{p.structure_type}</span>
                          <div className="flex items-center gap-1">
                            {getRiskIcon(p.risk_category || "Low")}
                            <span className="font-semibold">{p.risk_category || "Low"} Risk</span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* Institutional Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-[10.5px]">
          {sidebarOpen ? (
            <>
              <button
                onClick={() => setDataFreshnessOpen(true)}
                className="flex items-center gap-1.5 text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
              >
                <Clock size={12} className="text-emerald-400" />
                <span>Telemetry Freshness</span>
              </button>
              <span className="text-[10px] text-slate-500 font-mono">CGWB v2.0</span>
            </>
          ) : (
            <button
              onClick={() => setDataFreshnessOpen(true)}
              className="mx-auto text-slate-400 hover:text-emerald-400"
              title="Data Freshness"
            >
              <Clock size={14} />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};
