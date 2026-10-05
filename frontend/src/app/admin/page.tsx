"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Database,
  Cpu,
  RefreshCw,
  CheckCircle,
  AlertOctagon,
  Clock,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { useModelVersions, useRefreshLogs } from "@/lib/hooks/useData";
import { ModelVersion, DataRefreshLog } from "@/lib/types";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<"models" | "refresh">("models");

  const {
    data: modelVersions,
    isLoading: modelsLoading,
    error: modelsError,
    refetch: refetchModels,
  } = useModelVersions();

  const {
    data: refreshLogs,
    isLoading: logsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useRefreshLogs();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleTriggerRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Refetch both datasets from the backend
      await Promise.all([refetchModels(), refetchLogs()]);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10">
      {/* Top Header */}
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft size={18} />
            </Link>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-emerald-400">
                NeerNiti Admin & Management Panel
              </h1>
              <p className="text-xs text-slate-400">
                Model versioning, dataset telemetry sync, and system verification status
              </p>
            </div>
          </div>

          <button
            onClick={handleTriggerRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 font-bold text-xs text-slate-950 flex items-center justify-center gap-2 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
          >
            <RefreshCw size={15} className={isRefreshing ? "animate-spin" : ""} />
            {isRefreshing ? "Refreshing Data..." : "Refresh Data"}
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 border-b border-slate-800">
          <button
            onClick={() => setActiveTab("models")}
            className={`pb-3 px-4 text-xs font-bold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "models"
                ? "border-emerald-400 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Cpu size={15} /> Registered ML Models
          </button>
          <button
            onClick={() => setActiveTab("refresh")}
            className={`pb-3 px-4 text-xs font-bold flex items-center gap-2 border-b-2 transition-all ${
              activeTab === "refresh"
                ? "border-emerald-400 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Database size={15} /> Data Refresh Logs
          </button>
        </div>

        {/* Tab 1: Registered Models */}
        {activeTab === "models" && (
          <div className="space-y-4">
            {modelsLoading && (
              <div className="flex items-center justify-center py-16 text-slate-400 gap-2">
                <Loader2 size={18} className="animate-spin" /> Loading model versions...
              </div>
            )}
            {modelsError && (
              <div className="flex items-center justify-center py-16 text-red-400 gap-2">
                <AlertTriangle size={18} /> Failed to load models: {(modelsError as Error).message}
              </div>
            )}
            {modelVersions && modelVersions.length === 0 && (
              <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
                No model versions registered yet.
              </div>
            )}
            {modelVersions && modelVersions.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {modelVersions.map((model: ModelVersion) => (
                  <div
                    key={model.model_version_id}
                    className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold border border-emerald-500/30">
                        {model.module_name}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{model.model_version_id}</span>
                    </div>

                    <div>
                      <h3 className="font-extrabold text-sm text-slate-100">{model.algorithm}</h3>
                      <p className="text-[11px] text-slate-400">Trained: {model.trained_on}</p>
                    </div>

                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 space-y-1.5 font-mono text-[11px]">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans mb-1">
                        Evaluation Metrics
                      </div>
                      {Object.entries(model.evaluation_metrics).map(([key, val]) => (
                        <div key={key} className="flex justify-between text-slate-300">
                          <span className="text-slate-500">{key}:</span>
                          <span className="text-emerald-400 font-bold">{String(val)}</span>
                        </div>
                      ))}
                    </div>

                    <div className="text-[10px] text-slate-500 truncate" title={model.training_data_snapshot}>
                      Snapshot: <span className="font-mono text-slate-400">{model.training_data_snapshot}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Refresh Logs */}
        {activeTab === "refresh" && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 bg-slate-900/90 border-b border-slate-800 font-bold text-xs text-slate-300">
              Recent Telemetry & Satellite Data Sync Execution Log
            </div>

            {logsLoading && (
              <div className="flex items-center justify-center py-16 text-slate-400 gap-2">
                <Loader2 size={18} className="animate-spin" /> Loading refresh logs...
              </div>
            )}
            {logsError && (
              <div className="flex items-center justify-center py-16 text-red-400 gap-2">
                <AlertTriangle size={18} /> Failed to load logs: {(logsError as Error).message}
              </div>
            )}
            {refreshLogs && refreshLogs.length === 0 && (
              <div className="flex items-center justify-center py-16 text-slate-500 text-sm">
                No refresh logs found.
              </div>
            )}
            {refreshLogs && refreshLogs.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="p-3.5">Log ID</th>
                      <th className="p-3.5">Source Name</th>
                      <th className="p-3.5">Timestamp</th>
                      <th className="p-3.5">Status</th>
                      <th className="p-3.5">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {refreshLogs.map((log: DataRefreshLog) => (
                      <tr key={log.log_id} className="hover:bg-slate-800/40">
                        <td className="p-3.5 font-mono text-slate-400">{log.log_id.substring(0, 8)}</td>
                        <td className="p-3.5 font-semibold text-slate-200">{log.source_name}</td>
                        <td className="p-3.5 text-slate-400 flex items-center gap-1.5">
                          <Clock size={13} className="text-slate-500" /> {log.fetched_at}
                        </td>
                        <td className="p-3.5">
                          {log.status === "success" ? (
                            <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30 flex items-center gap-1 w-max text-[10px]">
                              <CheckCircle size={12} /> Success
                            </span>
                          ) : log.status === "failure" ? (
                            <span className="px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 font-semibold border border-red-500/30 flex items-center gap-1 w-max text-[10px]">
                              <AlertTriangle size={12} /> Failed
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/30 flex items-center gap-1 w-max text-[10px]">
                              <AlertOctagon size={12} /> Partial
                            </span>
                          )}
                        </td>
                        <td className="p-3.5 text-slate-400 italic">
                          {log.error_message || "Completed without errors"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
