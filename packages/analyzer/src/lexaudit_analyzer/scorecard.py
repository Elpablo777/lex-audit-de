"""Stufe D: Realistische Durchsetzungs-Hebel-Scorecard (BVerfG 2025 & § 47 VwGO / Petitionen)."""

from __future__ import annotations

from datetime import date, timedelta

from lexaudit_core.schemas import (
    ConflictClass,
    LeverageScorecard,
    LeverType,
    NormType,
)


def compute_leverage_scorecard(
    *,
    conflict_class: ConflictClass,
    norm_type: NormType,
    jurisdiction_level: str,
    land_code: str | None = None,
    promulgation_date: date | None = None,
    reference_date: date | None = None,
) -> LeverageScorecard:
    """Ordnet jeden Befund kalibriert dem wirksamsten juristischen oder politischen Hebel zu."""
    today = reference_date or date.today()

    # 1. Untergesetzliches Landes- oder Kommunalrecht (VO / Satzung) -> § 47 VwGO i.V.m. § 75 NJG
    if norm_type in {NormType.ORDINANCE, NormType.MUNICIPAL_STATUTE} and jurisdiction_level in {
        "land",
        "kommunal",
    }:
        deadline = (promulgation_date + timedelta(days=365)) if promulgation_date else None
        days_rem = (deadline - today).days if deadline else None
        land_hint = (
            "OVG Lüneburg (§ 47 VwGO i.V.m. § 75 NJG) — Stärkster direkter Hebel in Niedersachsen, "
            "da beim Nds. StGH keine Individual-Verfassungsbeschwerde existiert."
            if land_code == "NI"
            else "Zuständiges Oberverwaltungsgericht / VGH (§ 47 VwGO)."
        )
        return LeverageScorecard(
            primary_lever=LeverType.OVG_NORMENKONTROLLE_47_VWGO,
            secondary_levers=[LeverType.LANDTAG_PETITION, LeverType.ABGEORDNETEN_BRIEFING],
            realistic_success_band="Hoch bei objektiver Rechts-/EU-Kollision innerhalb 1-Jahres-Frist",
            nds_individual_constitutional_complaint_available=False,
            deadline_date=deadline,
            days_remaining=days_rem,
            cost_risk_note="Vertretungszwang (§ 67 Abs. 4 VwGO); Verfahrensbündelung über Umwelt-/Fachverbände empfohlen.",
            rationale=land_hint,
        )

    # 2. Horizontaler Schnittstellenbruch (Steuer/Soziales) -> Bundestag ePetition + Abgeordnete
    if conflict_class == ConflictClass.HORIZONTALER_SCHNITTSTELLENBRUCH:
        return LeverageScorecard(
            primary_lever=LeverType.BUNDESTAG_EPETITION,
            secondary_levers=[
                LeverType.ABGEORDNETEN_BRIEFING,
                LeverType.FACHGERICHT_VORLAGE_ART100,
            ],
            realistic_success_band="Politisch direkt adressierbar (30.000 Mitzeichnungen / 6 Wochen auf petition.bundestag.de)",
            nds_individual_constitutional_complaint_available=False,
            cost_risk_note="Keine Prozesskosten bei ePetition & Abgeordneten-Dossier; Sozialgerichts-Einzelklage erst nach Bescheid.",
            rationale=(
                "Systembrüche zwischen SGB II, WoGG, BKGG und EStG lassen sich nur durch Gesetzesintegration "
                "sauber lösen; eine direkte BVerfG-Beschwerde scheitert fast immer am Rechtsweg (2025: 1,12 % Erfolg)."
            ),
        )

    # 3. Formelles Bundesgesetz mit Verfassungs-/EU-Spannung -> Fachgerichtsvorlage Art. 100 GG / Art. 267 AEUV
    return LeverageScorecard(
        primary_lever=LeverType.FACHGERICHT_VORLAGE_ART100,
        secondary_levers=[
            LeverType.BUNDESTAG_EPETITION,
            LeverType.ABGEORDNETEN_BRIEFING,
            LeverType.VERFASSUNGSBESCHWERDE_ULTIMA_RATIO,
        ],
        realistic_success_band="Strukturiertes Verbands-/Fachanwalts-Dossier für Art.-100-GG-Vorlage deutlich realistischer als direkte Verfassungsbeschwerde (1,12 %)",
        nds_individual_constitutional_complaint_available=False,
        cost_risk_note=(
            "BVerfG 2025: 83,31 % Kammer-Nichtannahmen ohne Begründung; direkte Gesetzesbeschwerden nur 75 Eingänge. "
            "Kostenrisiko daher über Fachverbände oder Musterverfahren abfedern."
        ),
        rationale=(
            "Formelle Parlamentsgesetze können Fachgerichte nicht selbst verwerfen, sondern müssen sie nach "
            "Art. 100 Abs. 1 GG dem Bundesverfassungsgericht vorlegen (oder nach Art. 267 AEUV dem EuGH)."
        ),
    )
