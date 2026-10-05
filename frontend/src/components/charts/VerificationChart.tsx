"use client";

import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { VerificationLog } from "@/lib/types";
import { Hammer } from "lucide-react";

interface Props {
  logs: VerificationLog[];
  structureType?: string;
}

export const VerificationChart: React.FC<Props> = ({ logs, structureType }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="h-44 flex items-center justify-center text-slate-500 text-xs italic">
        No verification data available.
      </div>
    );
  }

  const chartData = logs.map((log) => ({
    date: log.date.substring(0, 7),
    predicted: log.predicted_m,
    actual: log.actual_m,
  }));

  return (
    <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-xl shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400">
            <Hammer size={16} />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-200">
              Bi-LSTM Performance Verification {structureType ? `(${structureType})` : ""}
            </h4>
            <p className="text-[10px] text-slate-400">Predicted vs Actual Water Table (m)</p>
          </div>
        </div>
      </div>

      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
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
              formatter={(value: any, name: any) => [
                `${Number(value).toFixed(2)}m`,
                name === "predicted" ? "Bi-LSTM Predicted" : "Actual Water Level",
              ]}
            />
            <Legend wrapperStyle={{ fontSize: "10px", color: "#94a3b8" }} />
            <Line
              type="monotone"
              dataKey="predicted"
              name="predicted"
              stroke="#00BCD4"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="actual"
              name="actual"
              stroke="#4CAF50"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
