"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { fetchJson } from "@/lib/api";
import type { GraphSnapshot } from "@/lib/types";

const LegalWebGLGraph = dynamic(
  () => import("@/components/LegalWebGLGraph").then((m) => m.LegalWebGLGraph),
  { ssr: false }
);

export default function GraphPage() {
  const [asOf, setAsOf] = useState("2026-11-27");
  const [level, setLevel] = useState("all");
  const [domain, setDomain] = useState("all");
  const [snapshot, setSnapshot] = useState<GraphSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const loadGraph = useCallback(async (dateVal: string, lvlVal: string, domVal: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ as_of: dateVal });
      if (lvlVal !== "all") params.set("jurisdiction_level", lvlVal);
      if (domVal !== "all") params.set("legal_domain", domVal);
      const snap = await fetchJson<GraphSnapshot>(`/api/v1/graph?${params.toString()}`);
      setSnapshot(snap);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph(asOf, level, domain);
  }, [asOf, level, domain, loadGraph]);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-editorial-ink">
          Interaktiver Rechts- &amp; Konflikt-Graph (Zeitreise &amp; Stufenbau)
        </h1>
        <p className="text-sm text-editorial-muted">
          Filtern Sie das bitemporale Wissensnetzwerk nach Rechts-Ebene, Rechtsgebiet und
          historischem Stichtag — jede Visualisierung ist per 1-Klick-Toggle als semantische
          HTML-Tabelle zugänglich.
        </p>
      </div>

      {/* Filterleiste */}
      <div className="grid grid-cols-1 gap-4 rounded-xl border border-editorial-border bg-white p-4 sm:grid-cols-3">
        <div>
          <label htmlFor="graph-date" className="block text-xs font-semibold text-editorial-muted">
            Stichtag (Zeitreise)
          </label>
          <input
            id="graph-date"
            type="date"
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            className="mt-1 w-full rounded-md border border-editorial-border px-3 py-1.5 text-sm"
          />
          <div className="mt-1.5 flex gap-2 text-xs">
            <button
              type="button"
              onClick={() => setAsOf("2024-06-01")}
              className="rounded bg-slate-100 px-2 py-0.5 hover:bg-slate-200"
            >
              2024-06-01
            </button>
            <button
              type="button"
              onClick={() => setAsOf("2026-11-27")}
              className="rounded bg-slate-100 px-2 py-0.5 hover:bg-slate-200"
            >
              Aktuell (2026-11-27)
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="graph-level" className="block text-xs font-semibold text-editorial-muted">
            Rechtsebene
          </label>
          <select
            id="graph-level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="mt-1 w-full rounded-md border border-editorial-border bg-white px-3 py-1.5 text-sm"
          >
            <option value="all">Alle Ebenen (EU, Bund, NI, Judikative)</option>
            <option value="eu">EU-Recht</option>
            <option value="bund">Bundesrecht</option>
            <option value="land">Landesrecht (Pilot Niedersachsen)</option>
            <option value="judikative">Rechtsprechung (BVerfG / EuGH / BVerwG)</option>
          </select>
        </div>

        <div>
          <label htmlFor="graph-domain" className="block text-xs font-semibold text-editorial-muted">
            Rechtsgebiet
          </label>
          <select
            id="graph-domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="mt-1 w-full rounded-md border border-editorial-border bg-white px-3 py-1.5 text-sm"
          >
            <option value="all">Alle Rechtsgebiete</option>
            <option value="Steuerrecht">Steuerrecht</option>
            <option value="Sozialrecht">Sozialrecht</option>
            <option value="Umweltrecht">Umweltrecht</option>
            <option value="Verfassungsrecht">Verfassungsrecht</option>
            <option value="Verwaltungsprozessrecht">Verwaltungsprozessrecht</option>
          </select>
        </div>
      </div>

      {loading && !snapshot ? (
        <div className="rounded-xl border border-editorial-border bg-white p-8 text-center text-sm text-editorial-muted">
          Lade bitemporalen Rechtsgraph...
        </div>
      ) : snapshot ? (
        <LegalWebGLGraph snapshot={snapshot} />
      ) : null}
    </div>
  );
}
