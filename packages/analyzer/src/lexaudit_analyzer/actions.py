"""Aktions-Generator: Regelgeprüfte Petitionen (Bundestag / Landtag NI / openPetition) & § 47 VwGO Briefings."""

from __future__ import annotations

import math
import re
from datetime import date, timedelta

from lexaudit_core.config import AI_TRANSPARENCY_NOTICE_DE
from lexaudit_core.schemas import (
    ConflictFinding,
    LegislativeBriefing,
    PetitionDraft,
    PetitionTargetPortal,
)

_URL_RE = re.compile(r"(?i)(?:https?://|www\.)\S+")
_INSULT_RE = re.compile(
    r"(?i)\b(verbrecher|korrupt|betrüger|lügner|idiot|kriminell|unfähig\s+person)\b"
)


class PetitionGenerator:
    """Erstellt und validiert Petitionstexte hart gegen Portal-Richtlinien (Stand Nov 2026)."""

    @staticmethod
    def calculate_openpetition_quorum(population: int) -> int:
        """Berechnet kommunale/regionale Quoren über f(x) = x^0,616 (Nds. Landtag gedeckelt bei 5.000)."""
        if population <= 0:
            return 100
        return min(5000, max(50, round(math.pow(population, 0.616))))

    @classmethod
    def validate_draft(cls, draft: PetitionDraft) -> PetitionDraft:
        errors: list[str] = []
        combined = f"{draft.title}\n{draft.summary}\n{draft.request_text}"

        if draft.target_portal == PetitionTargetPortal.BUNDESTAG_PETITION:
            if _URL_RE.search(combined):
                errors.append(
                    "Richtlinie petition.bundestag.de verbietet externe URLs im Petitionstext."
                )
            if _INSULT_RE.search(combined):
                errors.append(
                    "Richtlinie petition.bundestag.de verbietet personenbezogene Angriffe/Herabsetzungen."
                )
        elif _INSULT_RE.search(combined):
            errors.append("Sachlichkeitsgebot verletzt: Bitte personenbezogene Angriffe entfernen.")

        if len(draft.request_text.strip()) < 40:
            errors.append("Das eigentliche Petitionsbegehren muss mindestens 40 Zeichen umfassen.")

        return draft.model_copy(
            update={"validation_passed": len(errors) == 0, "validation_errors": errors}
        )

    @classmethod
    def build_from_finding(
        cls,
        finding: ConflictFinding,
        *,
        target_portal: PetitionTargetPortal = PetitionTargetPortal.BUNDESTAG_PETITION,
        population_scope: int | None = None,
        custom_text: str | None = None,
    ) -> PetitionDraft:
        refs = [f"{c.norm_or_ecli_ref} ({c.eli_or_ecli})" for c in finding.citations if c.verified]
        if target_portal == PetitionTargetPortal.BUNDESTAG_PETITION:
            portal_url = "https://petition.bundestag.de/"
            quorum = 30000
        elif target_portal == PetitionTargetPortal.LANDTAG_NIEDERSACHSEN:
            portal_url = "https://www.navo.niedersachsen.de/navo2/portal/online-petition"
            quorum = 5000
        else:
            portal_url = "https://www.openpetition.de/"
            quorum = (
                cls.calculate_openpetition_quorum(population_scope)
                if population_scope
                else 5000
            )

        request_body = custom_text or (
            f"Der Gesetz- bzw. Verordnungsgeber wird aufgefordert, den dokumentierten System- bzw. Normkonflikt "
            f"zu beheben: {finding.plain_language_summary} "
            f"Geprüfte Normgrundlagen: {', '.join(refs) or ', '.join(finding.legal_chain_ids)}. "
            f"Ziel ist eine rechtssichere, verfassungs- und europarechtskonforme Neuregelung ohne unzumutbare "
            f"Schnittstellenverluste."
        )
        # Automatische Entfernung etwaiger URLs im Standard-Text, falls Bundestag gewählt wurde
        if target_portal == PetitionTargetPortal.BUNDESTAG_PETITION and not custom_text:
            request_body = _URL_RE.sub("", request_body).strip()

        draft = PetitionDraft(
            target_portal=target_portal,
            portal_url=portal_url,
            title=f"Reformbedarf: {finding.title[:140]}",
            summary=finding.plain_language_summary[:350],
            request_text=request_body,
            legal_basis_refs=refs,
            quorum_required=quorum,
            quorum_window_weeks=6,
            population_scope=population_scope,
            ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
        )
        return cls.validate_draft(draft)


class LegislativeBriefingGenerator:
    """Erstellt strukturierte Dossiers für § 47 VwGO / Art. 100 GG zur Weitergabe an Verbände & Fachanwälte."""

    @staticmethod
    def build_briefing(
        finding: ConflictFinding, *, reference_date: date | None = None
    ) -> LegislativeBriefing:
        today = reference_date or date.today()
        deadline = finding.scorecard.deadline_date or (
            date(2026, 5, 15) + timedelta(days=365)
            if "nduenggewnpvo" in " ".join(finding.legal_chain_ids)
            else None
        )
        days_rem = (deadline - today).days if deadline else None
        court = (
            "Niedersächsisches Oberverwaltungsgericht (OVG Lüneburg) gemäß § 47 VwGO i.V.m. § 75 NJG"
            if "land:ni" in " ".join(finding.legal_chain_ids)
            else "Zuständiges Fachgericht mit Vorlagepflicht nach Art. 100 Abs. 1 GG / Art. 267 AEUV"
        )
        citations_md = "\n".join(
            f"- **{c.norm_or_ecli_ref}** (`{c.eli_or_ecli}` · Quelle: {c.source_url}): „{c.quoted_excerpt}“"
            for c in finding.citations
            if c.verified
        )
        z3_block = (
            f"\n## Z3-SMT-Rechenbeweis\n{finding.z3_counterexample.summary}\n"
            if finding.z3_counterexample
            else ""
        )
        deadline_line = (
            f"- **1-Jahres-Frist (§ 47 Abs. 2 VwGO):** Ablauf am `{deadline.isoformat()}` (noch **{days_rem} Tage**)\n"
            if deadline
            else ""
        )
        md = (
            f"# Normenkontroll- & Verbände-Briefing: {finding.title}\n\n"
            f"- **Befund-ID:** `{finding.finding_id}`\n"
            f"- **Rechtsgebiet:** {finding.legal_domain} ({finding.jurisdiction_scope})\n"
            f"- **Primärer Hebel:** `{finding.scorecard.primary_lever.value}`\n"
            f"- **Zuständiges Gericht:** {court}\n"
            f"{deadline_line}"
            f"- **Zulässigkeits-/Kostenhinweis:** {finding.scorecard.cost_risk_note}\n\n"
            f"## Sachliche Systemanalyse\n{finding.technical_legal_analysis}\n"
            f"{z3_block}\n"
            f"## Deterministisch verifizierte Primärquellen\n{citations_md}\n\n"
            f"---\n*{AI_TRANSPARENCY_NOTICE_DE}*\n"
        )
        return LegislativeBriefing(
            briefing_id=f"briefing-{finding.finding_id}",
            finding_id=finding.finding_id,
            title=finding.title,
            norm_target=", ".join(finding.legal_chain_ids[:3]),
            competent_court=court,
            deadline_date=deadline,
            days_remaining=days_rem,
            standing_requirements=finding.scorecard.cost_risk_note,
            verified_citations=[c for c in finding.citations if c.verified],
            markdown_dossier=md,
            ai_transparency_notice=AI_TRANSPARENCY_NOTICE_DE,
        )
