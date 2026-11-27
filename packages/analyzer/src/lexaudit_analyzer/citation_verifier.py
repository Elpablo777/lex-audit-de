"""Deterministischer CitationVerifier (Stufe D) — Harte Zitations-Brandmauer gegen Halluzinationen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lexaudit_core.guardrails import BudgetAndRateLimitGuard
from lexaudit_core.schemas import CitationProof, ConflictFinding, VerificationStatus
from lexaudit_core.storage import SQLiteStorageBackend


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass
class CitationVerifier:
    """Prüft jede generierte Norm- und Urteilsreferenz deterministisch gegen den lokalen Spiegel."""

    storage: SQLiteStorageBackend

    def verify_citation(self, proof: CitationProof) -> CitationProof:
        as_of: date = proof.as_of_date
        lookup = self.storage.lookup_full_text(proof.norm_or_ecli_ref, as_of=as_of)
        if lookup is None:
            return proof.model_copy(
                update={
                    "exact_match_in_mirror": False,
                    "status_at_date": "unverified",
                    "verified": False,
                    "rejection_reason": f"Referenz '{proof.norm_or_ecli_ref}' nicht im lokalen Textspiegel gefunden.",
                }
            )

        full_text, source_url, eli_or_ecli, status = lookup
        norm_full = _normalize(full_text)
        norm_quote = _normalize(proof.quoted_excerpt)
        if len(norm_quote) < 4 or norm_quote not in norm_full:
            return proof.model_copy(
                update={
                    "exact_match_in_mirror": False,
                    "status_at_date": status,
                    "verified": False,
                    "rejection_reason": (
                        f"Zitat-Ausschnitt nicht wörtlich im Volltext von '{proof.norm_or_ecli_ref}' belegt."
                    ),
                }
            )

        return proof.model_copy(
            update={
                "eli_or_ecli": eli_or_ecli,
                "source_url": source_url or proof.source_url,
                "exact_match_in_mirror": True,
                "status_at_date": status,
                "verified": True,
                "rejection_reason": None,
            }
        )

    def verify_finding(self, finding: ConflictFinding) -> ConflictFinding:
        if not finding.citations:
            return finding.model_copy(
                update={"verification_status": VerificationStatus.REJECTED_UNVERIFIED}
            )

        verified_proofs = [self.verify_citation(c) for c in finding.citations]
        all_ok = all(c.verified for c in verified_proofs)
        return finding.model_copy(
            update={
                "citations": verified_proofs,
                "verification_status": (
                    VerificationStatus.VERIFIED
                    if all_ok
                    else VerificationStatus.REJECTED_UNVERIFIED
                ),
            }
        )

    def verify_batch(
        self, findings: list[ConflictFinding], guard: BudgetAndRateLimitGuard | None = None
    ) -> list[ConflictFinding]:
        checked = [self.verify_finding(f) for f in findings]
        if guard is not None and checked:
            rejected = sum(
                1 for f in checked if f.verification_status == VerificationStatus.REJECTED_UNVERIFIED
            )
            guard.check_citation_error_rate(total=len(checked), rejected=rejected)
        return checked
