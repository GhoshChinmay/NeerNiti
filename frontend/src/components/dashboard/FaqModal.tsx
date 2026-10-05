"use client";

import React from "react";
import { useMapStore } from "@/store/map-store";
import { X, HelpCircle, BookOpen, ShieldCheck, Zap } from "lucide-react";

export const FaqModal: React.FC = () => {
  const { faqOpen, setFaqOpen } = useMapStore();

  if (!faqOpen) return null;

  const faqs = [
    {
      q: "How does NeerNiti recommend recharge sites?",
      a: "NeerNiti uses an XGBoost machine-learning model trained on multi-criteria satellite and hydrogeological layers (slope, soil permeability, NDVI, rainfall, drainage density, and aquifer depth) to score candidate grid points from 0.0 to 1.0.",
    },
    {
      q: "Are the AI recommendations explainable?",
      a: "Yes! Every single recommended site is paired with a SHAP TreeExplainer feature contribution breakdown, synthesized into a plain-language sentence explaining the exact reasons for the score.",
    },
    {
      q: "How is structure recharge verified post-construction?",
      a: "When a structure is built, NeerNiti links the nearest monitoring wells and forecasts expected water table levels using a Bi-LSTM model. If observed water levels deviate by >15% from expected recovery, the structure is flagged as 'Underperforming'.",
    },
    {
      q: "Does NeerNiti require IoT or physical hardware?",
      a: "No. NeerNiti is 100% software-only and cost-zero by design. It uses free-tier Earth observation satellites (Sentinel, Landsat, SRTM, GRACE-FO) and government open-data networks (CGWB/India-WRIS).",
    },
  ];

  return (
    <div className="fixed inset-0 z-[3000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-5 text-slate-100 max-h-[85vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400">
              <HelpCircle size={16} />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-slate-200">System FAQ & Methodology</h3>
              <p className="text-[11px] text-slate-400">Architecture, ML models, and domain guidance</p>
            </div>
          </div>
          <button
            onClick={() => setFaqOpen(false)}
            className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
          >
            <X size={16} />
          </button>
        </div>

        {/* FAQ List */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
          {faqs.map((item, idx) => (
            <div key={idx} className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-2xl space-y-1.5">
              <div className="font-bold text-slate-200 flex items-center gap-1.5">
                <span className="text-emerald-400">Q:</span> {item.q}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-4">
                {item.a}
              </p>
            </div>
          ))}
        </div>

        {/* Close Button */}
        <button
          onClick={() => setFaqOpen(false)}
          className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 font-bold text-xs text-slate-300 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
};
