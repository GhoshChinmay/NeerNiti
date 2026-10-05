"use client";

import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { WellReadingHistory } from "@/lib/types";
import { TrendingDown } from "lucide-react";

interface Props {
  data: WellReadingHistory[];
  stationCode?: string;
}

export const WaterLevelChart: React.FC<Props> = ({ data, stationCode }) => {
  if (!data || data.length === 0) {
    return (
      <div className="h-44 flex items-center justify-center text-slate-500 text-xs italic">
        No water level telemetry available.
      </div>
    );
  }

  const chartData = data.map((d) => ({
    date: d.date.substring(0, 7),
    level: d.water_level_m,
  }));

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
            <TrendingDown size={16} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200">
              Groundwater Depth History {stationCode ? `(${stationCode})` : ""}
            </h4>
            <p className="text-[10px] text-slate-400">Water table depth below surface (m)</p>
          </div>
        </div>
      </div>

      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="waterLevelGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2196F3" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#2196F3" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
            <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} />
            <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                borderRadius: "8px",
                fontSize: "11px",
                color: "#f8fafc",
              }}
              formatter={(value: any) => [`${Number(value).toFixed(2)}m`, "Depth"]}
            />
            <Area
              type="monotone"
              dataKey="level"
              stroke="#2196F3"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#waterLevelGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
