"use client";

import { useState } from "react";
import { CheckCircle2, Compass, ShieldAlert } from "lucide-react";
import { fetchJson } from "@/lib/api";
import type { AssistantResponse } from "@/lib/types";

export default function AssistantPage() {
  const [mode, setMode] = useState<"mode_a_public_compass" | "mode_b_research_copilot">(
    "mode_a_public_compass"
  );
  const [braoConfirmed, setBraoConfirmed] = useState(false);
  const [query, setQuery] = useState(
    "Wie wirken § 11b SGB II und § 19 WoGG im Einkommensanrechnungssystem zusammen?"
  );
  const [response, setResponse] = useState<AssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitQuery(qOverride?: string) {
    const q = qOverride ?? query;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchJson<AssistantResponse>("/api/v1/assistant/query", {
        method: "POST",
        body: JSON.stringify({
          query: q,
          mode,
          brao_supervised_confirmed: mode === "mode_b_research_copilot" ? braoConfirmed : false,
        }),
      });
      setResponse(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Anfrage fehlgeschlagen");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Compass className="h-6 w-6 text-editorial-accent" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-editorial-ink">
            Phase 5: Vernetzter Jura-Recherche-Assistent (Dual-Mode)
          </h1>
        </div>
        <p className="text-sm text-editorial-muted">
          Strikte Trennung zwischen öffentlichem abstraktem Bürger-Kompass (RDG-konform) und
          anwaltlich/volljuristisch verantwortetem Research-Copilot (§ 3 BRAO) über ZDR-geschützten
          Transport (<code>CitizenPrivacyLLMClient</code>).
        </p>
      </div>

      {/* Modus-Schalter */}
      <div className="rounded-xl border border-editorial-border bg-white p-5 space-y-4 shadow-sm">
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setMode("mode_a_public_compass")}
            aria-pressed={mode === "mode_a_public_compass"}
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${
              mode === "mode_a_public_compass"
                ? "bg-editorial-accent text-white"
                : "border border-editorial-border text-editorial-ink"
            }`}
          >
            Modus A · Öffentlicher Rechts-Kompass (RDG-konform)
          </button>
          <button
            type="button"
            onClick={() => setMode("mode_b_research_copilot")}
            aria-pressed={mode === "mode_b_research_copilot"}
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${
              mode === "mode_b_research_copilot"
                ? "bg-editorial-accent text-white"
                : "border border-editorial-border text-editorial-ink"
            }`}
          >
            Modus B · Jura-Research-Copilot (§ 3 BRAO)
          </button>
        </div>

        {mode === "mode_b_research_copilot" && (
          <label className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-editorial-ink">
            <input
              type="checkbox"
              checked={braoConfirmed}
              onChange={(e) => setBraoConfirmed(e.target.checked)}
            />
            <span>
              Ich bestätige den Einsatz zur fachjuristischen Recherche unter berufsrechtlicher
              Aufsicht und Verantwortung (§ 3 BRAO).
            </span>
          </label>
        )}

        <div className="space-y-2">
          <label htmlFor="assistant-query" className="block text-xs font-semibold text-editorial-muted">
            Rechts- oder Normketten-Anfrage
          </label>
          <textarea
            id="assistant-query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-lg border border-editorial-border p-3 text-sm"
          />

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => submitQuery()}
              disabled={loading}
              className="rounded-lg bg-editorial-accent px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              {loading ? "Prüfe gegen Volltextspiegel..." : "Verifizierte Auskunft abrufen"}
            </button>
            <button
              type="button"
              onClick={() => {
                const probe = "Habe ich in meinem konkreten Fall Anspruch auf Wohngeld?";
                setQuery(probe);
                submitQuery(probe);
              }}
              className="rounded-lg border border-amber-400 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950 hover:bg-amber-100"
            >
              RDG-Guardrail testen (Einzelfall-Probe)
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-editorial-danger">
          {error}
        </div>
      )}

      {response && (
        <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-4">
          {response.rdg_blocked ? (
            <div role="status" className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-editorial-danger">
              <div className="flex items-center gap-2 font-bold">
                <ShieldAlert className="h-5 w-5" aria-hidden="true" />
                <span>RDG-Schutzsperre aktiv (§ 2 Abs. 1 RDG)</span>
              </div>
              <p className="mt-1 text-xs">{response.rdg_reason}</p>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1 rounded bg-green-50 px-2.5 py-1 font-semibold text-editorial-ok">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                CitationVerifier: {response.verification_status}
              </span>
              <span className="rounded bg-slate-100 px-2.5 py-1">
                Datenschutz-Transport: {response.privacy_transport}
              </span>
            </div>
          )}

          <div className="whitespace-pre-line text-sm leading-relaxed text-editorial-ink">
            {response.answer}
          </div>

          {response.citations.length > 0 && (
            <div className="border-t border-slate-100 pt-3">
              <h2 className="text-xs font-semibold uppercase text-editorial-muted">
                Verifizierte Primärquellen
              </h2>
              <ul className="mt-2 space-y-1.5 text-xs">
                {response.citations.map((c) => (
                  <li key={c.citation_id} className="rounded bg-slate-50 p-2">
                    <strong>{c.norm_or_ecli_ref}</strong> ({c.eli_or_ecli}) — „{c.quoted_excerpt}“
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="rounded-lg bg-slate-50 p-3 text-xs text-editorial-muted">
            {response.ai_transparency_notice}
          </p>
        </section>
      )}
    </div>
  );
}
