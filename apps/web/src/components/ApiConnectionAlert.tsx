"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

interface ApiConnectionAlertProps {
  error: string | null;
  onRetry?: () => void;
}

export function ApiConnectionAlert({ error, onRetry }: ApiConnectionAlertProps) {
  if (!error) return null;

  return (
    <div
      role="alert"
      className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-editorial-danger space-y-2"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Backend-Verbindung fehlgeschlagen</span>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-2.5 py-1 text-xs font-semibold text-editorial-danger hover:bg-red-100"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Erneut verbinden</span>
          </button>
        )}
      </div>
      <p className="text-xs leading-relaxed text-red-950">{error}</p>
      <div className="rounded-md bg-white/80 px-3 py-2 font-mono text-[11px] text-slate-800">
        Vollstart: <strong>.\scripts\start_local.ps1</strong> oder API im zweiten Terminal:{" "}
        <strong>uv run uvicorn lexaudit_api.main:app --host 127.0.0.1 --port 8010</strong>
      </div>
    </div>
  );
}
