"use client";

import React from "react";
import { StructureFeature } from "@/lib/types";
import { Hammer, X, AlertTriangle, CheckCircle } from "lucide-react";

interface Props {
  feature: StructureFeature;
  onClose: () => void;
}

export const StructurePopup: React.FC<Props> = ({ feature, onClose }) => {
  const props = feature.properties;
  const logs = props.verification_logs || [];

  const isUnderperforming = props.current_status === "Underperforming";

  const statusColor = isUnderperforming
    ? "bg-red-500/20 text-red-400 border-red-500/30"
    : "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";

  return (
    <div className="w-80 bg-slate-900/95 text-slate-100 p-4 rounded-xl border border-slate-700/80 shadow-2xl backdrop-blur-md relative font-sans text-xs">
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
      >
        <X size={14} />
      </button>

      <div className="flex items-center gap-2 mb-2 pr-6">
        <div className={`p-1.5 rounded-lg ${isUnderperforming ? "bg-red-500/20 text-red-400" : "bg-cyan-500/20 text-cyan-400"}`}>
          <Hammer size={16} />
        </div>
        <div>
          <h3 className={`font-semibold text-sm ${isUnderperforming ? "text-red-400" : "text-cyan-400"}`}>
            Built {props.structure_type}
          </h3>
          <p className="text-[10px] text-slate-400">
            Constructed: {props.construction_date ? props.construction_date.substring(0, 10) : "N/A"}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50 mb-3">
        <span className="text-slate-400">Bi-LSTM Status:</span>
        <div className={`px-2 py-0.5 rounded-md text-[11px] font-bold border flex items-center gap-1 ${statusColor}`}>
          {isUnderperforming ? <AlertTriangle size={12} /> : <CheckCircle size={12} />}
          {props.current_status}
        </div>
      </div>

      <div className="space-y-1">
        <span className="font-medium text-slate-300 text-[11px]">Verification Telemetry Logs</span>
        {logs.length > 0 ? (
          <div className="max-h-32 overflow-y-auto rounded border border-slate-700/60 scrollbar-thin scrollbar-thumb-slate-700">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-800/90 text-slate-400 sticky top-0 border-b border-slate-700">
                <tr>
                  <th className="p-1.5">Date</th>
                  <th className="p-1.5">Pred</th>
                  <th className="p-1.5 text-right">Actual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {logs.map((log, i) => {
                  const isWarn = log.status === "Underperforming";
                  return (
                    <tr key={i} className="hover:bg-slate-800/40">
                      <td className="p-1.5 text-slate-300">{log.date.substring(0, 7)}</td>
                      <td className="p-1.5 text-slate-400">{log.predicted_m.toFixed(2)}m</td>
                      <td className={`p-1.5 text-right font-semibold ${isWarn ? "text-red-400" : "text-emerald-400"}`}>
                        {log.actual_m.toFixed(2)}m
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 italic text-[11px]">No verification logs yet.</p>
        )}
      </div>
    </div>
  );
};
