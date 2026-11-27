export interface CitationProof {
  citation_id: string;
  norm_or_ecli_ref: string;
  eli_or_ecli: string;
  norm_location: string;
  as_of_date: string;
  source_url: string;
  quoted_excerpt: string;
  exact_match_in_mirror: boolean;
  status_at_date: string;
  verified: boolean;
  rejection_reason: string | null;
}

export interface LeverageScorecard {
  primary_lever: string;
  secondary_levers: string[];
  realistic_success_band: string;
  bverfg_reference_rate: number;
  kammer_non_acceptance_rate: number;
  nds_individual_constitutional_complaint_available: boolean;
  deadline_date: string | null;
  days_remaining: number | null;
  cost_risk_note: string;
  rationale: string;
}

export interface Z3Counterexample {
  model_name: string;
  satisfiable: boolean;
  summary: string;
  inputs: Record<string, number | string>;
  outputs: Record<string, number | string>;
  legal_anchors: string[];
}

export interface ConflictFinding {
  finding_id: string;
  title: string;
  conflict_class: number;
  severity: "critical" | "high" | "medium" | "low";
  verification_status: "VERIFIED" | "REJECTED_UNVERIFIED";
  jurisdiction_scope: string;
  legal_domain: string;
  plain_language_summary: string;
  technical_legal_analysis: string;
  legal_chain_ids: string[];
  citations: CitationProof[];
  scorecard: LeverageScorecard;
  z3_counterexample: Z3Counterexample | null;
  ai_transparency_notice: string;
  generated_by_tier: string;
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  jurisdiction_level: string;
  hierarchy_rank: number;
  legal_domain: string;
  valid_from: string | null;
  valid_to: string | null;
  status: string;
  eli_or_ecli: string;
  has_conflict: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation_type: string;
  resolved: boolean;
  evidence: string;
}

export interface GraphSnapshot {
  as_of_date: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    nodes: number;
    edges: number;
    conflicts: number;
  };
}

export interface HealthResponse {
  status: string;
  corpus_stats: Record<string, number>;
  graph_stats: Record<string, number>;
  verified_findings_count: number;
  bverfg_2025: {
    year: number;
    total_filings: number;
    resolved: number;
    successful: number;
    success_rate: number;
    ten_year_avg_rate: number;
    kammer_non_acceptance_no_reason_rate: number;
    direct_statute_complaints: number;
    senate_decisions: number;
    nds_individual_constitutional_complaint: boolean;
  };
  ai_transparency_notice: string;
  llm_mode: string;
}

export interface HouseholdPoint {
  gross_income: number;
  net_income_estg: number;
  sgb2_benefit: number;
  wohngeld: number;
  kinderzuschlag: number;
  disposable_income: number;
  marginal_withdrawal_rate_pct: number;
}

export interface PetitionDraft {
  target_portal: "bundestag_petition" | "landtag_niedersachsen" | "openpetition";
  portal_url: string;
  title: string;
  summary: string;
  request_text: string;
  legal_basis_refs: string[];
  quorum_required: number;
  quorum_window_weeks: number;
  population_scope: number | null;
  validation_passed: boolean;
  validation_errors: string[];
  ai_transparency_notice: string;
}

export interface StatePortalDescriptor {
  land_code: string;
  land_name: string;
  portal_type: string;
  official_portal_url: string;
  gazette_url: string;
  machine_readable_status: string;
  notes: string;
}

export interface AssistantResponse {
  mode: "mode_a_public_compass" | "mode_b_research_copilot";
  rdg_blocked: boolean;
  rdg_reason: string | null;
  answer: string;
  citations: CitationProof[];
  verification_status: string;
  privacy_transport: string;
  ai_transparency_notice: string;
}
