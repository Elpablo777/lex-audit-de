import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import GraphPage from "@/app/graph/page";
import SimulatorPage from "@/app/simulator/page";
import { ConflictCausalFlow } from "@/components/ConflictCausalFlow";
import { LegalWebGLGraph } from "@/components/LegalWebGLGraph";
import type { ConflictFinding, GraphSnapshot } from "@/lib/types";

vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="react-flow-mock">{children}</div>
  ),
  Background: () => null,
  Controls: () => null,
  MiniMap: () => null,
}));

vi.mock("sigma", () => ({
  default: class MockSigma {
    on() {}
    kill() {}
  },
}));

const SAMPLE_FINDING: ConflictFinding = {
  finding_id: "finding-ni-nitrat-47vwgo",
  title: "Niedersachsen NDüngGewNPVO,NI vs. EU-Nitratrichtlinie",
  conflict_class: 1,
  severity: "high",
  verification_status: "VERIFIED",
  jurisdiction_scope: "EU / Bund / Niedersachsen",
  legal_domain: "Umweltrecht",
  plain_language_summary: "Abweichende Düngeregeln unterlaufen die EU-Nitratrichtlinie.",
  technical_legal_analysis: "Anwendungsvorrang des Unionsrechts.",
  legal_chain_ids: ["de:land:ni:nduenggewnpvo:p_2", "eu:dir:91_676_ewg:art_5"],
  citations: [],
  scorecard: {
    primary_lever: "ovg_normenkontrolle_47_vwgo",
    secondary_levers: ["landtag_petition"],
    realistic_success_band: "Hoch innerhalb 1-Jahres-Frist",
    bverfg_reference_rate: 0.0112,
    kammer_non_acceptance_rate: 0.8331,
    nds_individual_constitutional_complaint_available: false,
    deadline_date: "2027-05-15",
    days_remaining: 169,
    cost_risk_note: "Vertretungszwang § 67 Abs. 4 VwGO",
    rationale: "OVG Lüneburg prüft objektiv.",
  },
  z3_counterexample: null,
  ai_transparency_notice: "Hinweis nach Art. 50 KI-VO",
  generated_by_tier: "deterministic",
};

const SAMPLE_SNAPSHOT: GraphSnapshot = {
  as_of_date: "2026-11-27",
  nodes: [
    {
      id: "de:bund:gg:art_3",
      label: "GG Art. 3",
      node_type: "NormUnit",
      jurisdiction_level: "bund",
      hierarchy_rank: 3,
      legal_domain: "Verfassungsrecht",
      valid_from: "1949-05-24",
      valid_to: null,
      status: "in_force",
      eli_or_ecli: "eli/bund/bgbl-1/1949/s1/art_3",
      has_conflict: true,
    },
  ],
  edges: [],
  stats: { nodes: 1, edges: 0, conflicts: 1 },
};

describe("WCAG 2.2 Barrierefreiheit & Portal-Komponenten", () => {
  it("schaltet zwischen React Flow Kausalbaum und semantischer HTML-Tabelle per 1-Klick um", () => {
    render(<ConflictCausalFlow finding={SAMPLE_FINDING} />);
    expect(screen.getByTestId("react-flow-mock")).toBeInTheDocument();

    const toggleBtn = screen.getByRole("button", {
      name: /Als HTML-Tabelle anzeigen/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("de:land:ni:nduenggewnpvo:p_2")).toBeInTheDocument();
    expect(screen.getByText("eu:dir:91_676_ewg:art_5")).toBeInTheDocument();
  });

  it("schaltet zwischen Sigma.js WebGL-Graph und semantischer WCAG-HTML-Tabelle um", () => {
    render(<LegalWebGLGraph snapshot={SAMPLE_SNAPSHOT} />);
    const toggleBtn = screen.getByRole("button", {
      name: /Als semantische HTML-Tabelle anzeigen/i,
    });
    fireEvent.click(toggleBtn);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("GG Art. 3")).toBeInTheDocument();
    expect(screen.getByText("eli/bund/bgbl-1/1949/s1/art_3")).toBeInTheDocument();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("rendert im Z3-Simulator die Haushalts-Grenzbelastungstabelle inkl. >100%-Zeilen", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/z3/household")) {
        return new Response(
          JSON.stringify({
            z3_proof: {
              model_name: "Z3_Sozial_Steuer_Transferentzug_Pilot1",
              satisfiable: true,
              summary: "Grenzbelastung 107.0 %",
              inputs: { rent_eur: 850, children: 2 },
              outputs: { marginal_withdrawal_rate_pct: 107.0 },
              legal_anchors: ["§ 11b SGB II"],
            },
            curve: [
              {
                gross_income: 1200,
                net_income_estg: 966.61,
                sgb2_benefit: 0,
                wohngeld: 517.5,
                kinderzuschlag: 471.5,
                disposable_income: 2455.61,
                marginal_withdrawal_rate_pct: 107.7,
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(
        JSON.stringify({
          z3_proof: {
            model_name: "Z3_ErbStG_Gleichheitssatz_Pilot2",
            satisfiable: true,
            summary: "Großerwerb 0.99 % vs 10.50 %",
            inputs: { business_assets_mio: 120, private_assets_mio: 2 },
            outputs: { tax_due_mio: 1.0 },
            legal_anchors: ["§ 28a ErbStG"],
          },
          selected_point: {
            business_assets_mio: 120,
            private_assets_mio: 2,
            tax_due_mio: 1.0,
            effective_tax_rate_pct: 0.83,
            regime_applied: "§ 28a ErbStG",
          },
          curve: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    });

    render(<SimulatorPage />);

    await waitFor(() => {
      expect(screen.getByText(/Z3 SMT Ergebnis: SAT/i)).toBeInTheDocument();
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
    expect(screen.getByText("Grenzbelastung %")).toBeInTheDocument();
    expect(screen.getByText("107.7 %")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalled();
  });

  it("zeigt auf der Graph-Seite einen klaren deutschen Verbindungshinweis statt stillem Absturz", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    render(<GraphPage />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByText(/Backend-Verbindung fehlgeschlagen/i)).toBeInTheDocument();
    expect(screen.getAllByText(/uvicorn lexaudit_api\.main:app/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /Erneut verbinden/i })).toBeInTheDocument();
  });
});
