"""Verbindliche Pydantic-v2-Datenverträge für alle Schichten von LexAudit DE/EU."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from lexaudit_core.config import AI_TRANSPARENCY_NOTICE_DE, BVERFG_2025_STATS


class JurisdictionLevel(StrEnum):
    INTERNATIONAL = "international"
    EU = "eu"
    BUND = "bund"
    LAND = "land"
    KOMMUNAL = "kommunal"


class NormType(StrEnum):
    TREATY = "treaty"
    EU_REGULATION = "eu_regulation"
    EU_DIRECTIVE = "eu_directive"
    CONSTITUTION = "constitution"
    FORMAL_STATUTE = "formal_statute"
    ORDINANCE = "ordinance"
    MUNICIPAL_STATUTE = "municipal_statute"
    ADMIN_DIRECTIVE = "admin_directive"


class HierarchyRank(IntEnum):
    """Gerichteter Stufenbau der Rechtsordnung (1 = höchste Normebene)."""

    VOELKERRECHT_ALLG = 1
    EU_RECHT = 2
    GRUNDGESETZ = 3
    BUNDESRECHT = 4
    LANDESRECHT = 5
    KOMMUNAL_UND_VV = 6


class TemporalStatus(StrEnum):
    IN_FORCE = "in_force"
    REPEALED = "repealed"
    PENDING = "pending"
    EXPIRED = "expired"


class CourtLevel(StrEnum):
    EGMR = "egmr"
    EUGH = "eugh"
    BVERFG = "bverfg"
    OBERSTES_BUNDESGERICHT = "oberstes_bundesgericht"
    OVG_OBERLANDESGERICHT = "ovg_oberlandesgericht"
    FACHGERICHT = "fachgericht"


class ConflictClass(IntEnum):
    """Taxonomie der fünf prüfbaren Rechtsfehler."""

    VERTIKALE_NORMKOLLISION = 1
    VERFASSUNGS_PRINZIPIENBRUCH = 2
    HORIZONTALER_SCHNITTSTELLENBRUCH = 3
    LEGISTISCHER_MANGEL = 4
    RECHTSPRECHUNGS_DIVERGENZ = 5


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED_UNVERIFIED = "REJECTED_UNVERIFIED"


class ObligationType(StrEnum):
    PFLICHT_MUSS = "Pflicht_Muss"
    PFLICHT_SOLL = "Pflicht_Soll"
    ERMESSEN_KANN = "Ermessen_Kann"
    BEFUGNIS = "Befugnis"
    DEFINITION = "Definition"
    AUSNAHME = "Ausnahme"


class LeverType(StrEnum):
    OVG_NORMENKONTROLLE_47_VWGO = "ovg_normenkontrolle_47_vwgo"
    FACHGERICHT_VORLAGE_ART100 = "fachgericht_vorlage_art100"
    BUNDESTAG_EPETITION = "bundestag_epetition"
    LANDTAG_PETITION = "landtag_petition"
    ABGEORDNETEN_BRIEFING = "abgeordneten_briefing"
    VERFASSUNGSBESCHWERDE_ULTIMA_RATIO = "verfassungsbeschwerde_ultima_ratio"


class LegalAct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    act_id: str = Field(..., min_length=2)
    eli_uri: str | None = None
    title: str = Field(..., min_length=2)
    short_title: str = ""
    jurisdiction_level: JurisdictionLevel
    land_code: str | None = Field(default=None, description="z. B. 'NI', 'BY', 'NW'")
    norm_type: NormType
    hierarchy_rank: int = Field(..., ge=1, le=6)
    promulgation_date: date | None = None
    source_url: str
    license: str = "§ 5 UrhG gemeinfrei"


class NormUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    norm_id: str = Field(..., min_length=3)
    act_id: str = Field(..., min_length=2)
    eli_uri: str | None = None
    designation: str = Field(..., description="z. B. '§ 13a' oder 'Art. 3 Abs. 1'")
    heading: str = ""
    hierarchy_rank: int = Field(..., ge=1, le=6)
    legal_domain: str = "allgemein"
    status: TemporalStatus = TemporalStatus.IN_FORCE


class ComponentTemporalVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(..., min_length=3)
    norm_id: str = Field(..., min_length=3)
    valid_from: date
    valid_to: date | None = None
    promulgation_date: date | None = None
    status: TemporalStatus = TemporalStatus.IN_FORCE
    text_hash: str = Field(..., min_length=64, max_length=64)
    full_text: str = Field(..., min_length=1)
    context_header: str = Field(..., min_length=3)
    supersedes_version_id: str | None = None


class CourtDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., min_length=3)
    ecli: str = Field(..., min_length=5)
    court_level: CourtLevel
    court_name: str
    decision_date: date
    file_number: str
    leitsatz: str = ""
    tenor: str = ""
    full_text: str = Field(..., min_length=1)
    source_url: str
    license: str = "§ 5 UrhG gemeinfrei"


class ParliamentaryDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(..., min_length=3)
    issuer: str
    doc_number: str
    title: str
    summary: str = ""
    publication_date: date
    source_url: str
    license: str = "dl-de/by-2-0"


class LegalConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str
    term: str
    domain: str
    norm_id: str
    definition_text: str
    obligation_type: ObligationType
    addressee: str = "Allgemeinheit"
    condition_text: str = ""
    legal_consequence: str = ""


class CitationProof(BaseModel):
    """Deterministischer Verifikationsnachweis gegen den lokalen Volltextspiegel."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str
    norm_or_ecli_ref: str
    eli_or_ecli: str
    norm_location: str
    as_of_date: date
    source_url: str
    quoted_excerpt: str = Field(..., min_length=4)
    exact_match_in_mirror: bool = False
    status_at_date: TemporalStatus | str = TemporalStatus.IN_FORCE
    verified: bool = False
    rejection_reason: str | None = None


class LeverageScorecard(BaseModel):
    """Realistische Durchsetzungs-Empfehlung kalibriert an BVerfG 2025 & § 47 VwGO."""

    model_config = ConfigDict(extra="forbid")

    primary_lever: LeverType
    secondary_levers: list[LeverType] = Field(default_factory=list)
    realistic_success_band: str
    bverfg_reference_rate: float = BVERFG_2025_STATS["success_rate"]
    kammer_non_acceptance_rate: float = BVERFG_2025_STATS["kammer_non_acceptance_no_reason_rate"]
    nds_individual_constitutional_complaint_available: bool = False
    deadline_date: date | None = None
    days_remaining: int | None = None
    cost_risk_note: str
    rationale: str


class Z3Counterexample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    satisfiable: bool
    summary: str
    inputs: dict[str, float | int | str]
    outputs: dict[str, float | int | str]
    legal_anchors: list[str] = Field(default_factory=list)


class ConflictFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    title: str
    conflict_class: ConflictClass
    severity: Severity
    verification_status: VerificationStatus = VerificationStatus.REJECTED_UNVERIFIED
    jurisdiction_scope: str = "Bund / Niedersachsen"
    legal_domain: str = "Allgemein"
    plain_language_summary: str
    technical_legal_analysis: str
    legal_chain_ids: list[str] = Field(default_factory=list)
    citations: list[CitationProof] = Field(default_factory=list)
    scorecard: LeverageScorecard
    z3_counterexample: Z3Counterexample | None = None
    ai_transparency_notice: str = AI_TRANSPARENCY_NOTICE_DE
    generated_by_tier: str = "deterministic-hybrid"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _enforce_verification_invariant(self) -> ConflictFinding:
        """Ein Befund darf nur VERIFIED sein, wenn mindestens ein verifiziertes Zitat existiert und kein Zitat fehlgeschlagen ist."""
        if self.verification_status == VerificationStatus.VERIFIED and (
            not self.citations or any(not c.verified for c in self.citations)
        ):
            self.verification_status = VerificationStatus.REJECTED_UNVERIFIED
        return self


class PetitionTargetPortal(StrEnum):
    BUNDESTAG_PETITION = "bundestag_petition"
    LANDTAG_NIEDERSACHSEN = "landtag_niedersachsen"
    OPENPETITION = "openpetition"


class PetitionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_portal: PetitionTargetPortal
    portal_url: HttpUrl | str
    title: str = Field(..., min_length=5, max_length=180)
    summary: str = Field(..., min_length=10)
    request_text: str = Field(..., min_length=20)
    legal_basis_refs: list[str] = Field(default_factory=list)
    quorum_required: int
    quorum_window_weeks: int = 6
    population_scope: int | None = None
    validation_passed: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    ai_transparency_notice: str = AI_TRANSPARENCY_NOTICE_DE


class LegislativeBriefing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    briefing_id: str
    finding_id: str
    title: str
    norm_target: str
    competent_court: str
    deadline_date: date | None = None
    days_remaining: int | None = None
    standing_requirements: str
    verified_citations: list[CitationProof]
    markdown_dossier: str
    ai_transparency_notice: str = AI_TRANSPARENCY_NOTICE_DE


class AssistantMode(StrEnum):
    MODE_A_PUBLIC_COMPASS = "mode_a_public_compass"
    MODE_B_RESEARCH_COPILOT = "mode_b_research_copilot"


class AssistantQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=3, max_length=4000)
    mode: AssistantMode = AssistantMode.MODE_A_PUBLIC_COMPASS
    as_of_date: date | None = None
    brao_supervised_confirmed: bool = False


class AssistantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: AssistantMode
    rdg_blocked: bool = False
    rdg_reason: str | None = None
    answer: str
    citations: list[CitationProof] = Field(default_factory=list)
    verification_status: VerificationStatus
    privacy_transport: str
    ai_transparency_notice: str = AI_TRANSPARENCY_NOTICE_DE


class AuditRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    total_candidates: int = 0
    verified_count: int = 0
    rejected_count: int = 0
    citation_error_rate: float = 0.0
    estimated_cost_usd: float = 0.0
    status: str = "running"


class NormReference(BaseModel):
    """Deterministisch extrahierter Norm-Querverweis (QuantLaw-Stil)."""

    model_config = ConfigDict(extra="forbid")

    src_norm_id: str
    tgt_norm_id: str
    relation_type: str
    evidence: str
    resolved: bool
    raw_citation: str
