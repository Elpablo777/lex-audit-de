"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { CheckCircle2, Clock, ExternalLink, Scale } from "lucide-react";
import { CONFLICT_CLASS_LABELS, LEVER_LABELS, fetchJson } from "@/lib/api";
import type { ConflictFinding } from "@/lib/types";

const ConflictCausalFlow = dynamic(
  () => import("@/components/ConflictCausalFlow").then((m) => m.ConflictCausalFlow),
  { ssr: false }
);

interface NormTextItem {
  ref_id: string;
  eli_or_ecli: string;
  status: string;
  source_url: string;
  full_text: string;
}

interface FindingDetailPayload {
  finding: ConflictFinding;
  norm_texts: NormTextItem[];
  briefing: {
    competent_court: string;
    deadline_date: string | null;
    days_remaining: number | null;
    markdown_dossier: string;
  };
}

export default function FindingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<FindingDetailPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<FindingDetailPayload>(`/api/v1/findings/${id}`)
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Fehler"));
  }, [id]);

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-editorial-danger">
        Befund konnte nicht geladen werden: {error}
      </div>
    );
  }
  if (!data) {
    return <div className="p-8 text-sm text-editorial-muted">Lade Befunddetails...</div>;
  }

  const { finding, norm_texts, briefing } = data;

  return (
    <div className="space-y-8">
      <div className="space-y-3 rounded-2xl border border-editorial-border bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Link href="/findings" className="text-editorial-accent hover:underline">
            ← Alle Befunde
          </Link>
          <span>·</span>
          <span className="rounded bg-slate-100 px-2 py-0.5 font-semibold">
            {CONFLICT_CLASS_LABELS[finding.conflict_class]}
          </span>
          <span className="inline-flex items-center gap-1 rounded bg-green-50 px-2 py-0.5 font-semibold text-editorial-ok">
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
            {finding.verification_status}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-editorial-ink">{finding.title}</h1>
        <p className="text-base text-editorial-ink">{finding.plain_language_summary}</p>
        <p className="text-sm text-editorial-muted">{finding.technical_legal_analysis}</p>

        <div className="rounded-lg bg-slate-50 p-3 text-xs text-editorial-muted">
          {finding.ai_transparency_notice}
        </div>
      </div>

      {/* React Flow Kausalbaum + WCAG Tabelle */}
      <ConflictCausalFlow finding={finding} />

      {/* Z3 Rechenbeweis falls vorhanden */}
      {finding.z3_counterexample && (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-5 space-y-2">
          <h2 className="text-base font-bold text-amber-950">
            Mathematischer Z3-SMT-Gegenbeweis ({finding.z3_counterexample.model_name})
          </h2>
          <p className="text-sm text-amber-900">{finding.z3_counterexample.summary}</p>
          <div className="flex flex-wrap gap-3 text-xs">
            <Link
              href="/simulator"
              className="rounded-md bg-amber-800 px-3 py-1.5 font-semibold text-white hover:bg-amber-900"
            >
              Im Z3-Rechenlabor interaktiv testen →
            </Link>
          </div>
        </section>
      )}

      {/* Realistische Durchsetzungs-Hebel-Scorecard */}
      <section className="rounded-xl border border-editorial-border bg-white p-6 shadow-sm space-y-3">
        <div className="flex items-center gap-2">
          <Scale className="h-5 w-5 text-editorial-accent" aria-hidden="true" />
          <h2 className="text-lg font-bold text-editorial-ink">
            Realistische Hebel-Scorecard (kalibriert auf BVerfG 2025)
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-editorial-border p-4 space-y-1.5">
            <div className="text-xs font-semibold uppercase text-editorial-muted">Primärer Hebel</div>
            <div className="text-base font-bold text-editorial-accent">
              {LEVER_LABELS[finding.scorecard.primary_lever] ?? finding.scorecard.primary_lever}
            </div>
            <p className="text-xs text-editorial-ink">{finding.scorecard.rationale}</p>
            {briefing.deadline_date && (
              <p className="mt-2 inline-flex items-center gap-1.5 rounded bg-blue-50 px-2.5 py-1 text-xs font-semibold text-editorial-accent">
                <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                1-Jahres-Frist (§ 47 VwGO): {briefing.deadline_date} (noch {briefing.days_remaining} Tage)
              </p>
            )}
          </div>

          <div className="rounded-lg border border-editorial-border p-4 space-y-1.5">
            <div className="text-xs font-semibold uppercase text-editorial-muted">
              Kostenrisiko &amp; BVerfG-Realität
            </div>
            <p className="text-xs text-editorial-ink">{finding.scorecard.cost_risk_note}</p>
            <div className="pt-2 flex flex-wrap gap-2">
              <Link
                href={`/aktionen?finding=${finding.finding_id}`}
                className="rounded-md bg-editorial-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
              >
                Petition / Abgeordneten-Brief / § 47 VwGO Dossier erstellen →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Side-by-Side Normvergleich + CitationProof */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-editorial-ink">
          Side-by-Side-Normvergleich &amp; deterministisch verifizierte Primärzitate
        </h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {norm_texts.map((nt) => (
            <div
              key={nt.ref_id}
              className="rounded-xl border border-editorial-border bg-white p-4 space-y-2"
            >
              <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
                <span className="font-mono text-xs font-bold text-editorial-accent">{nt.ref_id}</span>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px]">{nt.status}</span>
              </div>
              <p className="text-xs leading-relaxed text-editorial-ink whitespace-pre-line">
                {nt.full_text}
              </p>
              <div className="flex items-center justify-between pt-1 text-[11px] text-editorial-muted">
                <span className="truncate">{nt.eli_or_ecli}</span>
                <a
                  href={nt.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-editorial-accent hover:underline"
                >
                  Amtliche Quelle <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-xl border border-editorial-border bg-white p-4">
          <h3 className="text-sm font-semibold text-editorial-ink">
            Protokoll des CitationVerifier
          </h3>
          <ul className="mt-2 space-y-2 text-xs">
            {finding.citations.map((c) => (
              <li key={c.citation_id} className="rounded border border-green-200 bg-green-50 p-2.5">
                <div className="font-semibold text-editorial-ok">
                  ✓ Verifiziert: {c.norm_or_ecli_ref} ({c.eli_or_ecli})
                </div>
                <div className="mt-1 text-editorial-ink">„{c.quoted_excerpt}“</div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
