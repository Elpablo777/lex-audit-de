"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Calculator } from "lucide-react";
import { ApiConnectionAlert } from "@/components/ApiConnectionAlert";
import { fetchJson, formatApiError } from "@/lib/api";
import type { HouseholdPoint, Z3Counterexample } from "@/lib/types";

interface HouseholdSimResponse {
  z3_proof: Z3Counterexample;
  curve: HouseholdPoint[];
}

interface ErbstgPoint {
  business_assets_mio: number;
  private_assets_mio: number;
  tax_due_mio: number;
  effective_tax_rate_pct: number;
  regime_applied: string;
}

interface ErbstgSimResponse {
  z3_proof: Z3Counterexample;
  selected_point: ErbstgPoint;
  curve: ErbstgPoint[];
}

export default function SimulatorPage() {
  const [rent, setRent] = useState(850);
  const [children, setChildren] = useState(2);
  const [hhData, setHhData] = useState<HouseholdSimResponse | null>(null);

  const [assetsMio, setAssetsMio] = useState(120);
  const [privateMio, setPrivateMio] = useState(2);
  const [erbData, setErbData] = useState<ErbstgSimResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadHousehold = useCallback(() => {
    fetchJson<HouseholdSimResponse>(
      `/api/v1/z3/household?rent=${rent}&children=${children}&threshold_pct=100`
    )
      .then((res) => {
        setHhData(res);
        setError(null);
      })
      .catch((err: unknown) => setError(formatApiError(err)));
  }, [rent, children]);

  const loadErbstg = useCallback(() => {
    fetchJson<ErbstgSimResponse>(
      `/api/v1/z3/erbstg?business_assets_mio=${assetsMio}&private_assets_mio=${privateMio}`
    )
      .then((res) => {
        setErbData(res);
        setError(null);
      })
      .catch((err: unknown) => setError(formatApiError(err)));
  }, [assetsMio, privateMio]);

  useEffect(() => {
    loadHousehold();
  }, [loadHousehold]);

  useEffect(() => {
    loadErbstg();
  }, [loadErbstg]);

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-editorial-ink">
          Neuro-Symbolisches Z3-Rechenbeweis-Labor
        </h1>
        <p className="text-sm text-editorial-muted">
          Statt fehleranfälliger LLM-Kopfrechnung beweist der Z3 SMT Solver mathematisch exakte
          Schnittstellenbrüche und regressive Belastungssprünge.
        </p>
      </div>

      <ApiConnectionAlert
        error={error}
        onRetry={() => {
          loadHousehold();
          loadErbstg();
        }}
      />

      {/* Pilot 1: SGB II / WoGG / Kinderzuschlag / EStG */}
      <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-5">
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-editorial-accent" aria-hidden="true" />
          <h2 className="text-lg font-bold text-editorial-ink">
            Pilot 1: Sozial-Steuer-Schnittstelle (§ 11b SGB II · § 19 WoGG · § 6a BKGG · § 32a EStG)
          </h2>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="slider-rent" className="flex justify-between text-sm font-medium">
              <span>Warmmiete monatlich</span>
              <span className="font-bold tabular-nums">{rent} €</span>
            </label>
            <input
              id="slider-rent"
              type="range"
              min={400}
              max={1600}
              step={50}
              value={rent}
              onChange={(e) => setRent(Number(e.target.value))}
              className="mt-2 w-full accent-editorial-accent"
            />
          </div>

          <div>
            <label htmlFor="slider-children" className="flex justify-between text-sm font-medium">
              <span>Kinder im Haushalt</span>
              <span className="font-bold tabular-nums">{children}</span>
            </label>
            <input
              id="slider-children"
              type="range"
              min={0}
              max={5}
              step={1}
              value={children}
              onChange={(e) => setChildren(Number(e.target.value))}
              className="mt-2 w-full accent-editorial-accent"
            />
          </div>
        </div>

        {hhData?.z3_proof && (
          <div
            role="status"
            className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
          >
            <div className="flex items-center gap-2 font-bold">
              <AlertTriangle className="h-4 w-4 text-amber-700" aria-hidden="true" />
              <span>Z3 SMT Ergebnis: {hhData.z3_proof.satisfiable ? "SAT (Gegenbeweis gefunden)" : "UNSAT"}</span>
            </div>
            <p className="mt-1">{hhData.z3_proof.summary}</p>
          </div>
        )}

        {hhData && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-xs sm:text-sm">
              <caption className="mb-2 text-left text-xs text-editorial-muted">
                Effektive Grenzbelastung bei +100 € Brutto-Schritten (SGB II, WoGG, KiZ &amp; EStG)
              </caption>
              <thead>
                <tr className="border-b border-editorial-border bg-slate-50 text-xs uppercase text-editorial-muted">
                  <th scope="col" className="px-3 py-2">Brutto €</th>
                  <th scope="col" className="px-3 py-2">Netto EStG €</th>
                  <th scope="col" className="px-3 py-2">SGB II €</th>
                  <th scope="col" className="px-3 py-2">WoGG €</th>
                  <th scope="col" className="px-3 py-2">KiZ €</th>
                  <th scope="col" className="px-3 py-2">Verfügbar €</th>
                  <th scope="col" className="px-3 py-2">Grenzbelastung %</th>
                </tr>
              </thead>
              <tbody>
                {hhData.curve
                  .filter((_, idx) => idx % 2 === 0 || hhData.curve[idx]!.marginal_withdrawal_rate_pct >= 80)
                  .map((pt) => (
                    <tr
                      key={pt.gross_income}
                      className={`border-b border-slate-100 tabular-nums ${
                        pt.marginal_withdrawal_rate_pct > 100
                          ? "bg-red-50 font-semibold text-editorial-danger"
                          : pt.marginal_withdrawal_rate_pct >= 80
                            ? "bg-amber-50"
                            : ""
                      }`}
                    >
                      <td className="px-3 py-1.5">{pt.gross_income.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.net_income_estg.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.sgb2_benefit.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.wohngeld.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.kinderzuschlag.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.disposable_income.toFixed(0)}</td>
                      <td className="px-3 py-1.5">{pt.marginal_withdrawal_rate_pct.toFixed(1)} %</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Pilot 2: ErbStG § 13a / § 13c / § 28a */}
      <section className="rounded-2xl border border-editorial-border bg-white p-6 shadow-sm space-y-5">
        <h2 className="text-lg font-bold text-editorial-ink">
          Pilot 2: Erbschaftsteuer-Schwellenwerte (§ 13a · § 13c · § 28a ErbStG vs. Art. 3 Abs. 1 GG)
        </h2>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="slider-erbstg-assets" className="flex justify-between text-sm font-medium">
              <span>Begünstigtes Betriebsvermögen</span>
              <span className="font-bold tabular-nums">{assetsMio} Mio. €</span>
            </label>
            <input
              id="slider-erbstg-assets"
              type="range"
              min={5}
              max={300}
              step={5}
              value={assetsMio}
              onChange={(e) => setAssetsMio(Number(e.target.value))}
              className="mt-2 w-full accent-editorial-accent"
            />
          </div>

          <div>
            <label htmlFor="slider-erbstg-priv" className="flex justify-between text-sm font-medium">
              <span>Verfügbares Privatvermögen (§ 28a-Prüfung)</span>
              <span className="font-bold tabular-nums">{privateMio} Mio. €</span>
            </label>
            <input
              id="slider-erbstg-priv"
              type="range"
              min={0}
              max={40}
              step={1}
              value={privateMio}
              onChange={(e) => setPrivateMio(Number(e.target.value))}
              className="mt-2 w-full accent-editorial-accent"
            />
          </div>
        </div>

        {erbData && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-editorial-border bg-slate-50 p-4 space-y-1 text-sm">
              <div className="text-xs font-semibold uppercase text-editorial-muted">
                Ausgewählter Erwerbsfall
              </div>
              <div className="text-xl font-bold tabular-nums text-editorial-accent">
                Effektive Steuerquote: {erbData.selected_point.effective_tax_rate_pct.toFixed(2)} %
              </div>
              <div>Steuerlast: {erbData.selected_point.tax_due_mio.toFixed(3)} Mio. €</div>
              <div className="text-xs text-editorial-muted">{erbData.selected_point.regime_applied}</div>
            </div>
            <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950">
              <strong>Z3 SMT Gleichheits-Check:</strong> {erbData.z3_proof.summary}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
