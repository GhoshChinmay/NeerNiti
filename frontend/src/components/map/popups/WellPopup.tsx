"use client";

import React from "react";
import { WellFeature } from "@/lib/types";
import { Droplet, X } from "lucide-react";

interface Props {
  feature: WellFeature;
  onClose: () => void;
}

export const WellPopup: React.FC<Props> = ({ feature, onClose }) => {
  const props = feature.properties;
  const history = [...props.reading_history].reverse();

  return (
    <div className="w-72 bg-slate-900/95 text-slate-100 p-4 rounded-xl border border-slate-700/80 shadow-2xl backdrop-blur-md relative font-sans text-xs">
      <button
        onClick={onClose}
        className="absolute top-2 right-2 text-slate-400 hover:text-white p-1 rounded-lg transition-colors"
      >
        <X size={14} />
      </button>

      <div className="flex items-center gap-2 mb-2 pr-6">
        <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
          <Droplet size={16} />
        </div>
        <div>
          <h3 className="font-semibold text-sm text-blue-400">Groundwater Well</h3>
          <p className="text-[10px] text-slate-400">Station: {props.station_code || "N/A"}</p>
        </div>
      </div>

      <div className="space-y-1.5 mb-3 bg-slate-800/60 p-2.5 rounded-lg border border-slate-700/50">
        <div className="flex justify-between">
          <span className="text-slate-400">Source:</span>
          <span className="font-medium text-slate-200">{props.source}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Latest Level:</span>
          <span className="font-bold text-blue-400">
            {props.latest_water_level_m !== null
              ? `${props.latest_water_level_m.toFixed(2)}m`
              : "N/A"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Date:</span>
          <span className="text-slate-300">
            {props.reading_date ? props.reading_date.substring(0, 10) : "N/A"}
          </span>
        </div>
      </div>

      <div className="space-y-1">
        <span className="font-medium text-slate-300 text-[11px]">Telemetry History</span>
        {history.length > 0 ? (
          <div className="max-h-32 overflow-y-auto rounded border border-slate-700/60 scrollbar-thin scrollbar-thumb-slate-700">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-800/90 text-slate-400 sticky top-0 border-b border-slate-700">
                <tr>
                  <th className="p-1.5">Date</th>
                  <th className="p-1.5 text-right">Depth</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {history.map((reading, i) => (
                  <tr key={i} className="hover:bg-slate-800/40">
                    <td className="p-1.5 text-slate-300">{reading.date.substring(0, 7)}</td>
                    <td className="p-1.5 text-right font-semibold text-blue-400">
                      {reading.water_level_m.toFixed(2)}m
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 italic text-[11px]">No historical data available.</p>
        )}
      </div>
    </div>
  );
};
