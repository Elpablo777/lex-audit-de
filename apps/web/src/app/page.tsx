"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, CheckCircle2, Globe, ShieldCheck } from "lucide-react";
import { ApiConnectionAlert } from "@/components/ApiConnectionAlert";
import { CONFLICT_CLASS_LABELS, LEVER_LABELS, apiUrl, fetchJson, formatApiError } from "@/lib/api";
import type { ConflictFinding, HealthResponse, StatePortalDescriptor } from "@/lib/types";

interface AuditStreamLog {
  step: string;
  progress_pct: number;
  message: string;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [states, setStates] = useState<StatePortalDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [streamLogs, setStreamLogs] = useState<AuditStreamLog[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [liveProbe, setLiveProbe] = useState<Record<string, { ok: boolean; sample?: string; count?: number; error?: string }> | null>(null);
  const [probing, setProbing] = useState(false);

  const loadInitialData = () => {
    setError(null);
    Promise.all([
      fetchJson<HealthResponse>("/api/v1/health"),
      fetchJson<ConflictFinding[]>("/api/v1/findings"),
      fetchJson<StatePortalDescriptor[]>("/api/v1/states"),
    ])
      .then(([h, f, s]) => {
        setHealth(h);
        setFindings(f);
        setStates(s);
      })
      .catch((err: unknown) => {
        setError(formatApiError(err));
      });
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  function runLiveAuditStream() {
    setStreamLogs([]);
    setStreaming(true);
    const es = new EventSource(apiUrl("/api/v1/audits/stream"));
    es.addEventListener("audit", (ev) => {
      try {
        const parsed = JSON.parse((ev as MessageEvent<string>).data) as AuditStreamLog;
        setStreamLogs((prev) => [...prev, parsed]);
        if (parsed.progress_pct >= 100) {
          es.close();
          setStreaming(false);
          fetchJson<ConflictFinding[]>("/api/v1/findings").then(setFindings).catch(() => {});
        }
      } catch {
        es.close();
        setStreaming(false);
      }
    });
    es.onerror = () => {
      es.close();
      setStreaming(false);
    };
  }

  async function runLiveSourceProbe() {
    setProbing(true);
    try {
      const res = await fetchJson<Record<string, { ok: boolean; sample?: string; count?: number; error?: string }>>(
        "/api/v1/sources/live-probe"
      );
      setLiveProbe(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Live-Probe fehlgeschlagen");
    } finally {
      setProbing(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Editorial Hero */}
      <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div className="max-w-3xl space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-editorial-accent">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Zero-Token-Core · Z3 SMT · CitationVerifier · Pilot Niedersachsen &amp; Bund
            </span>
            <h1 className="text-2xl font-bold tracking-tight text-editorial-ink sm:text-3xl">
              Föderales Rechts-Audit- &amp; Demokratie-Portal für Deutschland und die EU
            </h1>
            <p className="text-sm leading-relaxed text-editorial-muted sm:text-base">
              Verknüpft Völkerrecht, EU-Recht, Grundgesetz, Bundesrecht und Landesrecht in einem{" "}
              <strong>bitemporalen Wissensgraph</strong>, beweist Schnittstellenbrüche mathematisch
              mit Z3 und übersetzt verifizierte Befunde in realistische rechtliche und politische
              Durchsetzungshebel.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={runLiveAuditStream}
              disabled={streaming}
              className="inline-flex items-center gap-2 rounded-lg bg-editorial-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              <Activity className="h-4 w-4" aria-hidden="true" />
              <span>{streaming ? "Audit läuft..." : "Live-Audit ausführen (SSE)"}</span>
            </button>
            <Link
              href="/graph"
              className="inline-flex items-center gap-2 rounded-lg border border-editorial-border px-4 py-2.5 text-sm font-semibold text-editorial-ink hover:bg-slate-50"
            >
              <span>WebGL-Rechtsgraph öffnen</span>
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </div>

        {error && (
          <div className="mt-4">
            <ApiConnectionAlert error={error} onRetry={loadInitialData} />
          </div>
        )}

        {streamLogs.length > 0 && (
          <div className="mt-5 rounded-lg border border-editorial-border bg-slate-50 p-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-editorial-muted">
              Live-Audit-Fortschritt (Server-Sent Events)
            </h2>
            <ul className="mt-2 space-y-1 text-xs font-mono">
              {streamLogs.map((log, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-10 text-right font-bold text-editorial-accent">
                    {log.progress_pct}%
                  </span>
                  <span className="text-editorial-muted">[{log.step}]</span>
                  <span className="text-editorial-ink">{log.message}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* BVerfG 2025 Realitätscheck */}
      <section aria-labelledby="realitaetscheck-heading" className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="realitaetscheck-heading" className="text-lg font-bold text-editorial-ink">
            Rechtsschutz-Realitätscheck (Amtliche BVerfG-Jahresstatistik 2025)
          </h2>
          <span className="text-xs text-editorial-muted">
            Grundlage für unsere realistische Hebel-Scorecard (keine falschen Klage-Versprechen)
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-editorial-border bg-white p-4">
            <p className="text-xs font-medium text-editorial-muted">Eingänge 2025 (BVerfG)</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-editorial-ink">
              {health ? health.bverfg_2025.total_filings.toLocaleString("de-DE") : "4.722"}
            </p>
            <p className="mt-1 text-xs text-editorial-muted">
              Davon nur {health ? health.bverfg_2025.direct_statute_complaints : 75} direkte
              Gesetzesbeschwerden (1,59 %)
            </p>
          </div>

          <div className="rounded-xl border border-editorial-border bg-white p-4">
            <p className="text-xs font-medium text-editorial-muted">Erfolgsquote 2025</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-editorial-danger">1,12 %</p>
            <p className="mt-1 text-xs text-editorial-muted">
              55 von 4.916 erledigten Verfahren · 10-J-Schnitt: 1,48 %
            </p>
          </div>

          <div className="rounded-xl border border-editorial-border bg-white p-4">
            <p className="text-xs font-medium text-editorial-muted">Nichtannahme ohne Begründung</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-editorial-warn">83,31 %</p>
            <p className="mt-1 text-xs text-editorial-muted">
              3.924 von 4.710 Kammerbeschlüssen · Nur 16 Senatsentscheidungen
            </p>
          </div>

          <div className="rounded-xl border border-editorial-border bg-white p-4">
            <p className="text-xs font-medium text-editorial-muted">Pilot Niedersachsen</p>
            <p className="mt-1 text-lg font-bold text-editorial-accent">§ 47 VwGO / § 75 NJG</p>
            <p className="mt-1 text-xs text-editorial-muted">
              Keine Bürger-Verfassungsbeschwerde beim Nds. StGH → OVG Lüneburg (1-Jahres-Frist)
            </p>
          </div>
        </div>
      </section>

      {/* Verifizierte Pilot-Befunde */}
      <section aria-labelledby="findings-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="findings-heading" className="text-lg font-bold text-editorial-ink">
            Verifizierte Audit-Befunde ({findings.length} · CitationVerifier-geprüft)
          </h2>
          <Link href="/findings" className="text-sm font-semibold text-editorial-accent hover:underline">
            Alle Befunde &amp; Filter →
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {findings.map((f) => (
            <article
              key={f.finding_id}
              className="flex flex-col justify-between rounded-xl border border-editorial-border bg-white p-5 shadow-sm"
            >
              <div className="space-y-2.5">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-editorial-ink">
                    {CONFLICT_CLASS_LABELS[f.conflict_class] ?? `Klasse ${f.conflict_class}`}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded bg-green-50 px-2 py-0.5 font-semibold text-editorial-ok">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    {f.verification_status} ({f.citations.length} Quellen)
                  </span>
                </div>
                <h3 className="text-base font-bold text-editorial-ink">{f.title}</h3>
                <p className="text-sm text-editorial-muted">{f.plain_language_summary}</p>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs">
                <span className="font-medium text-editorial-accent">
                  Hebel: {LEVER_LABELS[f.scorecard.primary_lever] ?? f.scorecard.primary_lever}
                </span>
                <Link
                  href={`/findings/${f.finding_id}`}
                  className="font-semibold text-editorial-ink hover:underline"
                >
                  Details &amp; Dossier →
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Live-Quellen-Probe & 16-Länder-Konnektoren */}
      <section className="rounded-xl border border-editorial-border bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-editorial-ink">
              Amtliche Schnittstellen &amp; 16 Bundesländer (StateLawConnector)
            </h2>
            <p className="text-xs text-editorial-muted">
              {states.length} Bundesländer mit robots.txt-Guard (§ 44b UrhG) registriert · Live-Probe
              gegen NeuRIS, Nds. Verkündung, Abgeordnetenwatch, OLDP, EUR-Lex &amp; HUDOC
            </p>
          </div>
          <button
            type="button"
            onClick={runLiveSourceProbe}
            disabled={probing}
            className="inline-flex items-center gap-2 rounded-lg border border-editorial-accent px-3 py-1.5 text-xs font-semibold text-editorial-accent hover:bg-slate-50"
          >
            <Globe className="h-4 w-4" aria-hidden="true" />
            <span>{probing ? "Prüfe Live-APIs..." : "Live-APIs jetzt prüfen"}</span>
          </button>
        </div>

        {liveProbe && (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(liveProbe).map(([name, info]) => (
              <div
                key={name}
                className={`rounded-lg border p-2.5 text-xs ${
                  info.ok
                    ? "border-green-300 bg-green-50 text-emerald-950"
                    : "border-amber-300 bg-amber-50 text-amber-950"
                }`}
              >
                <div className="font-semibold">{name}</div>
                <div className="mt-0.5 break-words text-[11px]">
                  {info.ok
                    ? `OK · ${info.sample ?? `${info.count ?? 1} Treffer`}`
                    : `Fehler: ${info.error ?? "unbekannt"}`}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
