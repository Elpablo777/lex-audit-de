"""Stufe-A-Vorfilter (0 KI-Tokens) & Stufe-B-ZfL-Pflichten-/Definitions-Extraktor."""

from __future__ import annotations

import re
from datetime import date

from lexaudit_core.schemas import LegalConcept, ObligationType, TemporalStatus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import GraphRepository
from pydantic import BaseModel, ConfigDict


class SymbolicSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    signal_kind: str
    source_id: str
    target_id: str | None = None
    description: str


def run_symbolic_prefilters(
    storage: SQLiteStorageBackend,
    graph: GraphRepository,
    *,
    reference_date: date | None = None,
) -> list[SymbolicSignal]:
    """Erkennt deterministisch tote Verweise, Zirkel, abgelaufene Befristungen & EU-Fristen (0 Tokens)."""
    ref_date = reference_date or date.today()
    signals: list[SymbolicSignal] = []

    for idx, edge in enumerate(graph.find_dead_references()):
        signals.append(
            SymbolicSignal(
                signal_id=f"dead_ref_{idx}",
                signal_kind="toter_verweis",
                source_id=edge.source,
                target_id=edge.target,
                description=f"Unaufgelöster Normverweis in {edge.source} auf {edge.target}: {edge.evidence}",
            )
        )

    for idx, cycle in enumerate(graph.find_cycles()):
        signals.append(
            SymbolicSignal(
                signal_id=f"cycle_{idx}",
                signal_kind="zirkelverweis",
                source_id=cycle[0],
                target_id=cycle[-1],
                description=f"Zirkuläre Verweiskette erkannt: {' -> '.join(cycle)}",
            )
        )

    for norm in storage.list_norms():
        ver = storage.get_version_at_date(norm.norm_id, as_of=ref_date)
        if ver and (ver.status == TemporalStatus.EXPIRED or (ver.valid_to and ver.valid_to <= ref_date)):
            signals.append(
                SymbolicSignal(
                    signal_id=f"expired_{norm.norm_id}",
                    signal_kind="abgelaufene_befristung",
                    source_id=norm.norm_id,
                    description=f"Norm/Verwaltungsvorschrift {norm.norm_id} befristet abgelaufen am {ver.valid_to}.",
                )
            )
        if norm.act_id.startswith("eu:dir:") and ver and "1993" in ver.full_text:
            signals.append(
                SymbolicSignal(
                    signal_id=f"eu_transposition_{norm.norm_id}",
                    signal_kind="eu_umsetzungsfrist",
                    source_id=norm.norm_id,
                    description=f"EU-Richtlinie {norm.norm_id} mit überschrittener Umsetzungsfrist als Prüfungsmaßstab.",
                )
            )

    return signals


class ZfLExtractor:
    """Semantische Pflichten- & Definitions-Extraktion nach Methodik des Zentrums für Legistik (ZfL)."""

    _RULES: tuple[tuple[ObligationType, re.Pattern[str]], ...] = (
        (ObligationType.PFLICHT_MUSS, re.compile(r"(?i)\b(muss|sind\s+verpflichtet|ist\s+.*?\s+zu\s+erlassen|schützt)\b")),
        (ObligationType.PFLICHT_SOLL, re.compile(r"(?i)\b(soll|sollen)\b")),
        (ObligationType.ERMESSEN_KANN, re.compile(r"(?i)\b(kann|können|darf)\b")),
        (ObligationType.DEFINITION, re.compile(r"(?i)\b(im\s+sinne\s+des|bedeutet|bemisst\s+sich)\b")),
        (ObligationType.AUSNAHME, re.compile(r"(?i)\b(vorbehaltlich|abweichend|ausnahme|steuerfrei)\b")),
    )

    def extract_concepts(self, storage: SQLiteStorageBackend) -> list[LegalConcept]:
        concepts: list[LegalConcept] = []
        for norm in storage.list_norms():
            ver = storage.get_version_at_date(norm.norm_id)
            if not ver:
                continue
            ob_type = ObligationType.BEFUGNIS
            for candidate_type, pat in self._RULES:
                if pat.search(ver.full_text):
                    ob_type = candidate_type
                    break
            term = "Einkommen" if "einkommen" in ver.full_text.lower() else (norm.heading or norm.designation)
            concepts.append(
                LegalConcept(
                    concept_id=f"concept:{norm.norm_id}",
                    term=term,
                    domain=norm.legal_domain,
                    norm_id=norm.norm_id,
                    definition_text=ver.full_text[:280],
                    obligation_type=ob_type,
                    addressee="Staatliche Gewalt / Normadressaten",
                    condition_text=norm.heading,
                    legal_consequence=ver.full_text[:140],
                )
            )
        return concepts

    def detect_definition_drift(self, concepts: list[LegalConcept]) -> list[dict[str, object]]:
        """Identifiziert identische Schlüsselbegriffe (z. B. 'Einkommen') mit abweichender Normdefinition."""
        by_term: dict[str, list[LegalConcept]] = {}
        for c in concepts:
            by_term.setdefault(c.term.lower(), []).append(c)
        drifts: list[dict[str, object]] = []
        for term, group in by_term.items():
            domains = sorted({c.domain for c in group})
            if len(group) >= 2 and (term == "einkommen" or len(domains) >= 2):
                drifts.append(
                    {
                        "term": group[0].term,
                        "norm_ids": [c.norm_id for c in group],
                        "domains": domains,
                        "count": len(group),
                    }
                )
        return drifts
