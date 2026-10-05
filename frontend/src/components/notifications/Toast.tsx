"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AlertTriangle, X } from "lucide-react";
import { getSocket } from "@/lib/socket";

interface ToastMessage {
  id: string;
  title: string;
  message: string;
}

const TOAST_DISMISS_MS = 8000;

export const Toast: React.FC = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const socket = getSocket();
    if (!socket) return;

    socket.connect();

    socket.on("structure_alert", (data: { title: string; message: string }) => {
      const newToast: ToastMessage = {
        id: Math.random().toString(),
        title: data.title || "Telemetry Alert",
        message: data.message || "Underperforming structure detected.",
      };
      setToasts((prev) => [...prev, newToast]);

      // Auto-dismiss after timeout
      setTimeout(() => {
        removeToast(newToast.id);
      }, TOAST_DISMISS_MS);
    });

    return () => {
      socket.off("structure_alert");
      socket.disconnect();
    };
  }, [removeToast]);

  return (
    <div className="fixed bottom-5 right-5 z-[3000] flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="bg-slate-900/95 border border-red-500/40 text-slate-100 p-3.5 rounded-xl shadow-2xl backdrop-blur-md flex items-start gap-3 animate-in slide-in-from-bottom-2"
        >
          <div className="p-1.5 bg-red-500/20 text-red-400 rounded-lg shrink-0">
            <AlertTriangle size={16} />
          </div>
          <div className="flex-1 text-xs">
            <div className="font-bold text-red-400">{toast.title}</div>
            <div className="text-slate-300 mt-0.5">{toast.message}</div>
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="text-slate-500 hover:text-white transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
};
