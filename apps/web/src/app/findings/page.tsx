"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { CONFLICT_CLASS_LABELS, LEVER_LABELS, fetchJson } from "@/lib/api";
import type { ConflictFinding } from "@/lib/types";

export default function FindingsListPage() {
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [domainFilter, setDomainFilter] = useState("all");

  useEffect(() => {
    const q = domainFilter === "all" ? "" : `?legal_domain=${encodeURIComponent(domainFilter)}`;
    fetchJson<ConflictFinding[]>(`/api/v1/findings${q}`)
      .then(setFindings)
      .catch(() => {});
  }, [domainFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-editorial-ink">
            Verifizierte Konflikt- &amp; Schnittstellenbefunde
          </h1>
          <p className="text-sm text-editorial-muted">
            Nur Befunde mit 100 % deterministisch verifizierten Primärquellen (`CitationVerifier`)
            erreichen dieses Portal.
          </p>
        </div>

        <div>
          <label htmlFor="domain-select" className="block text-xs font-semibold text-editorial-muted">
            Rechtsgebiet filtern
          </label>
          <select
            id="domain-select"
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="mt-1 rounded-md border border-editorial-border bg-white px-3 py-1.5 text-sm"
          >
            <option value="all">Alle Rechtsgebiete</option>
            <option value="Steuerrecht">Steuerrecht</option>
            <option value="Sozialrecht">Sozialrecht</option>
            <option value="Umweltrecht">Umweltrecht</option>
          </select>
        </div>
      </div>

      <div className="space-y-4">
        {findings.map((f) => (
          <article
            key={f.finding_id}
            className="rounded-xl border border-editorial-border bg-white p-6 shadow-sm space-y-3"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded bg-slate-100 px-2.5 py-1 font-semibold">
                {CONFLICT_CLASS_LABELS[f.conflict_class]}
              </span>
              <span className="rounded bg-blue-50 px-2.5 py-1 font-medium text-editorial-accent">
                {f.jurisdiction_scope}
              </span>
              <span className="inline-flex items-center gap-1 rounded bg-green-50 px-2.5 py-1 font-semibold text-editorial-ok">
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                {f.citations.length} verifizierte Primärzitate
              </span>
            </div>

            <h2 className="text-lg font-bold text-editorial-ink">{f.title}</h2>
            <p className="text-sm leading-relaxed text-editorial-muted">
              {f.plain_language_summary}
            </p>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs">
              <span>
                <strong>Empfohlener Hebel:</strong>{" "}
                {LEVER_LABELS[f.scorecard.primary_lever] ?? f.scorecard.primary_lever}
              </span>
              <Link
                href={`/findings/${f.finding_id}`}
                className="rounded-md bg-editorial-accent px-3 py-1.5 font-semibold text-white hover:bg-slate-800"
              >
                Kausalbaum, Normvergleich &amp; Aktionen →
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
