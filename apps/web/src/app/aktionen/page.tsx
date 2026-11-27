"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, FileText, Mail, Send } from "lucide-react";
import { fetchJson } from "@/lib/api";
import type { ConflictFinding, PetitionDraft, StatePortalDescriptor } from "@/lib/types";

interface RepresentativeResponse {
  postal_code: string;
  legal_domain: string;
  representatives: Array<{
    politician: string;
    parliament: string;
    constituency: string;
    committees: string[];
    api_source?: string;
  }>;
  letter_template: string;
}

export default function ActionsPage() {
  const [findings, setFindings] = useState<ConflictFinding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState("finding-ni-nitrat-47vwgo");
  const [portal, setPortal] = useState<
    "bundestag_petition" | "landtag_niedersachsen" | "openpetition"
  >("bundestag_petition");
  const [customText, setCustomText] = useState("");
  const [population, setPopulation] = useState(50000);
  const [petition, setPetition] = useState<PetitionDraft | null>(null);

  const [postalCode, setPostalCode] = useState("30159");
  const [domain, setDomain] = useState("Umweltrecht");
  const [reps, setReps] = useState<RepresentativeResponse | null>(null);

  const [states, setStates] = useState<StatePortalDescriptor[]>([]);
  const [dngLand, setDngLand] = useState("BB");
  const [dngText, setDngText] = useState("");
  const [briefingMd, setBriefingMd] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<ConflictFinding[]>("/api/v1/findings").then(setFindings).catch(() => {});
    fetchJson<StatePortalDescriptor[]>("/api/v1/states").then(setStates).catch(() => {});
  }, []);

  async function buildPetition(overrideText?: string) {
    setActionError(null);
    try {
      const res = await fetchJson<PetitionDraft>("/api/v1/actions/petition", {
        method: "POST",
        body: JSON.stringify({
          finding_id: selectedFinding,
          target_portal: portal,
          population_scope: portal === "openpetition" ? population : null,
          custom_text: (overrideText ?? customText).trim() || null,
        }),
      });
      setPetition(res);
      if (!overrideText && !customText) {
        setCustomText(res.request_text);
      }
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Petitions-Prüfung fehlgeschlagen");
    }
  }

  async function loadReps() {
    setActionError(null);
    try {
      const res = await fetchJson<RepresentativeResponse>(
        `/api/v1/actions/representatives?postal_code=${encodeURIComponent(
          postalCode
        )}&legal_domain=${encodeURIComponent(domain)}&finding_id=${encodeURIComponent(
          selectedFinding
        )}`
      );
      setReps(res);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Abgeordneten-Abfrage fehlgeschlagen");
    }
  }

  async function loadBriefing() {
    try {
      const res = await fetchJson<{ markdown_dossier: string }>(
        `/api/v1/actions/briefing/${encodeURIComponent(selectedFinding)}`
      );
      setBriefingMd(res.markdown_dossier);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Briefing konnte nicht geladen werden");
    }
  }

  async function generateDng() {
    setActionError(null);
    try {
      const res = await fetchJson<{ dng_request_text: string }>(
        `/api/v1/states/${encodeURIComponent(dngLand)}/dng-request`,
        { method: "POST", body: JSON.stringify({}) }
      );
      setDngText(res.dng_request_text);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "DNG-Antrag fehlgeschlagen");
    }
  }

  useEffect(() => {
    if (selectedFinding) {
      buildPetition("");
      loadBriefing();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFinding, portal]);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-editorial-ink">
          Demokratische Aktions-Werkzeuge &amp; Normenkontroll-Briefing
        </h1>
        <p className="text-sm text-editorial-muted">
          Erzeugen Sie regelgeprüfte Petitionen (<code>petition.bundestag.de</code>,
          Niedersächsischer Landtag, openPetition), adressieren Sie Abgeordnete über
          Abgeordnetenwatch API v2 oder exportieren Sie ein §-47-VwGO-Dossier für Verbände &amp; Fachanwälte.
        </p>
      </div>

      {/* Befund-Auswahl */}
      {actionError && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-editorial-danger">
          {actionError}
        </div>
      )}
      <div className="rounded-xl border border-editorial-border bg-white p-4">
        <label htmlFor="action-finding-select" className="block text-xs font-semibold text-editorial-muted">
          Ausgangsbefund wählen
        </label>
        <select
          id="action-finding-select"
          value={selectedFinding}
          onChange={(e) => {
            setCustomText("");
            setSelectedFinding(e.target.value);
          }}
          className="mt-1 w-full rounded-md border border-editorial-border bg-white px-3 py-2 text-sm"
        >
          {findings.map((f) => (
            <option key={f.finding_id} value={f.finding_id}>
              {f.title}
            </option>
          ))}
        </select>
      </div>

      {/* 1. Petitions-Assistent */}
      <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Send className="h-5 w-5 text-editorial-accent" aria-hidden="true" />
          <h2 className="text-lg font-bold text-editorial-ink">
            1. Regelgeprüfter Petitions-Assistent
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label htmlFor="petition-portal" className="block text-xs font-semibold text-editorial-muted">
              Zielportal
            </label>
            <select
              id="petition-portal"
              value={portal}
              onChange={(e) =>
                setPortal(
                  e.target.value as "bundestag_petition" | "landtag_niedersachsen" | "openpetition"
                )
              }
              className="mt-1 w-full rounded-md border border-editorial-border bg-white px-3 py-2 text-sm"
            >
              <option value="bundestag_petition">
                Bundestag (petition.bundestag.de · Quorum 30.000)
              </option>
              <option value="landtag_niedersachsen">
                Nds. Landtag Online-Petition (Quorum 5.000)
              </option>
              <option value="openpetition">
                openPetition (f(x) = x^0,616 / NI 5.000)
              </option>
            </select>
          </div>

          {portal === "openpetition" && (
            <div>
              <label htmlFor="petition-pop" className="block text-xs font-semibold text-editorial-muted">
                Einwohnerzahl Gebiet (für f(x)=x^0,616)
              </label>
              <input
                id="petition-pop"
                type="number"
                value={population}
                onChange={(e) => setPopulation(Number(e.target.value))}
                className="mt-1 w-full rounded-md border border-editorial-border px-3 py-2 text-sm"
              />
            </div>
          )}

          {petition && (
            <div className="rounded-lg bg-slate-50 p-3 text-xs">
              <div>
                <strong>Erforderliches Quorum:</strong>{" "}
                {petition.quorum_required.toLocaleString("de-DE")} Mitzeichnungen in{" "}
                {petition.quorum_window_weeks} Wochen
              </div>
              <div className="mt-1 text-editorial-muted">
                Hinweis: Altes epetitionen.bundestag.de schaltet am 30.12.2026 ab; neu gilt
                petition.bundestag.de (keine externen URLs!).
              </div>
            </div>
          )}
        </div>

        <div>
          <label htmlFor="petition-text" className="block text-xs font-semibold text-editorial-muted">
            Petitionstext (automatisch geprüft auf URL-Verbot &amp; Sachlichkeitsgebot)
          </label>
          <textarea
            id="petition-text"
            rows={4}
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            className="mt-1 w-full rounded-md border border-editorial-border p-3 text-sm"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => buildPetition(customText)}
              className="rounded-lg bg-editorial-accent px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              Regel-Check &amp; Entwurf aktualisieren
            </button>
          </div>
        </div>

        {petition && (
          <div
            role="status"
            className={`rounded-lg border p-3 text-xs ${
              petition.validation_passed
                ? "border-green-200 bg-green-50 text-editorial-ok"
                : "border-red-200 bg-red-50 text-editorial-danger"
            }`}
          >
            {petition.validation_passed ? (
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                <span>
                  Alle Portal-Regeln bestanden · Ziel: {String(petition.portal_url)}
                </span>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="flex items-center gap-2 font-semibold">
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  <span>Regelverstoß erkannt — Einreichung würde abgelehnt:</span>
                </div>
                <ul className="list-disc pl-5">
                  {petition.validation_errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 2. Abgeordneten-Router */}
      <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-editorial-accent" aria-hidden="true" />
          <h2 className="text-lg font-bold text-editorial-ink">
            2. Abgeordneten- &amp; Ausschuss-Router (Abgeordnetenwatch API v2 · CC0)
          </h2>
        </div>

        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label htmlFor="rep-plz" className="block text-xs font-semibold text-editorial-muted">
              PLZ
            </label>
            <input
              id="rep-plz"
              value={postalCode}
              onChange={(e) => setPostalCode(e.target.value)}
              className="mt-1 w-32 rounded-md border border-editorial-border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label htmlFor="rep-domain" className="block text-xs font-semibold text-editorial-muted">
              Rechtsgebiet / Ausschuss
            </label>
            <select
              id="rep-domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="mt-1 rounded-md border border-editorial-border bg-white px-3 py-1.5 text-sm"
            >
              <option value="Umweltrecht">Umweltrecht</option>
              <option value="Sozialrecht">Sozialrecht</option>
              <option value="Steuerrecht">Steuerrecht</option>
            </select>
          </div>
          <button
            type="button"
            onClick={loadReps}
            className="rounded-lg bg-editorial-accent px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Zuständige Mandate &amp; Briefvorlage laden
          </button>
        </div>

        {reps && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2">
              {reps.representatives.map((r, i) => (
                <div key={i} className="rounded-lg border border-editorial-border p-3 text-xs">
                  <div className="font-bold text-editorial-ink">{r.politician}</div>
                  <div className="text-editorial-muted">
                    {r.parliament} · {r.constituency}
                  </div>
                  <div className="mt-1">Ausschüsse: {r.committees.join(", ")}</div>
                </div>
              ))}
            </div>
            <pre className="whitespace-pre-wrap rounded-lg border border-editorial-border bg-slate-50 p-3 text-xs">
              {reps.letter_template}
            </pre>
          </div>
        )}
      </section>

      {/* 3. Normenkontroll-Dossier & DNG-Open-Data-Generator */}
      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-editorial-accent" aria-hidden="true" />
            <h2 className="text-base font-bold text-editorial-ink">
              3. Normenkontroll-Dossier (§ 47 VwGO / Art. 100 GG)
            </h2>
          </div>
          <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-lg border border-editorial-border bg-slate-50 p-3 text-xs">
            {briefingMd || "Lade Dossier..."}
          </pre>
        </div>

        <div className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-3">
          <h2 className="text-base font-bold text-editorial-ink">
            4. 16-Länder DNG-Open-Data-Anfrage-Generator
          </h2>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="dng-land" className="block text-xs font-semibold text-editorial-muted">
                Bundesland
              </label>
              <select
                id="dng-land"
                value={dngLand}
                onChange={(e) => setDngLand(e.target.value)}
                className="mt-1 rounded-md border border-editorial-border bg-white px-3 py-1.5 text-sm"
              >
                {states.map((s) => (
                  <option key={s.land_code} value={s.land_code}>
                    {s.land_code} · {s.land_name} ({s.machine_readable_status})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={generateDng}
              className="rounded-lg border border-editorial-accent px-3 py-1.5 text-xs font-semibold text-editorial-accent hover:bg-slate-50"
            >
              DNG-Antrag erzeugen
            </button>
          </div>
          {dngText && (
            <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg border border-editorial-border bg-slate-50 p-3 text-xs">
              {dngText}
            </pre>
          )}
        </div>
      </section>
    </div>
  );
}
