"use client";

import React, { useState } from "react";
import { useMapStore } from "@/store/map-store";
import { createStructure } from "@/lib/api-client";
import { X, Hammer, Calendar, CheckCircle2, AlertCircle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

export const MarkAsBuiltModal: React.FC = () => {
  const queryClient = useQueryClient();
  const { markAsBuiltSite, closeMarkAsBuiltModal, closeSiteDetail } = useMapStore();
  const [structureType, setStructureType] = useState<string>("Check Dam");
  const [buildDate, setBuildDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!markAsBuiltSite) return null;

  const siteProps = markAsBuiltSite.properties;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);

    try {
      await createStructure({
        site_id: siteProps.recommendation_id,
        structure_type: structureType,
        build_date: buildDate,
        status: "active",
      });

      // Invalidate queries to refresh data across UI
      await queryClient.invalidateQueries({ queryKey: ["recommendations"] });
      await queryClient.invalidateQueries({ queryKey: ["structures"] });

      closeMarkAsBuiltModal();
      closeSiteDetail();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register structure");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[3000] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-5 text-slate-100">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <Hammer size={16} />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-slate-200">Mark Site as Built</h3>
              <p className="text-[11px] text-slate-400">Transition recommendation to active monitoring</p>
            </div>
          </div>
          <button
            onClick={closeMarkAsBuiltModal}
            className="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
          >
            <X size={16} />
          </button>
        </div>

        {errorMsg && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 text-xs">
            <AlertCircle size={14} className="shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold">Structure Type</label>
            <select
              value={structureType}
              onChange={(e) => setStructureType(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 outline-none focus:border-emerald-500"
            >
              <option value="Check Dam">Check Dam</option>
              <option value="Percolation Tank">Percolation Tank</option>
              <option value="Recharge Well">Recharge Well</option>
              <option value="Farm Pond">Farm Pond</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-slate-300 font-semibold flex items-center gap-1.5">
              <Calendar size={13} className="text-cyan-400" /> Construction Date
            </label>
            <input
              type="date"
              value={buildDate}
              onChange={(e) => setBuildDate(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 outline-none focus:border-emerald-500"
              required
            />
          </div>

          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-[11px] text-slate-400 space-y-1">
            <div className="font-semibold text-slate-300">Automated Pipeline Actions:</div>
            <div>• Associates site coordinates with nearest monitoring wells (ST_DWithin).</div>
            <div>• Registers structure in Bi-LSTM scheduled verification monitoring.</div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeMarkAsBuiltModal}
              className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 font-bold text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 font-extrabold text-slate-950 shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <CheckCircle2 size={15} /> {submitting ? "Registering..." : "Confirm Build"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
