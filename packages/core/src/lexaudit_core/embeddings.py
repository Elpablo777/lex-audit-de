"""Domain-Chunking (entlang von §/Absatz-Grenzen) & Embedding-Adapter (Qwen3-4B / BGE-M3 / Deterministisch)."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.schemas import ComponentTemporalVersion, CourtDecision


class DomainChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    parent_id: str
    chunk_kind: str
    chunk_index: int
    context_header: str
    content: str
    embedding: list[float]


_ABSATZ_SPLIT_RE = re.compile(r"(?=\(\d{1,2}[a-z]?\)\s)")


def chunk_temporal_version(
    version: ComponentTemporalVersion,
    *,
    embedder: EmbeddingAdapter,
    max_chars: int = 1000,
) -> list[DomainChunk]:
    """Teilt eine Normfassung strikt entlang von Absatz-/§-Grenzen und stellt den Kontext-Header voran."""
    parts = [p.strip() for p in _ABSATZ_SPLIT_RE.split(version.full_text) if p.strip()]
    if not parts:
        parts = [version.full_text.strip()]

    merged: list[str] = []
    current = ""
    for part in parts:
        if len(current) + len(part) + 1 <= max_chars or not current:
            current = f"{current}\n{part}".strip() if current else part
        else:
            merged.append(current)
            current = part
    if current:
        merged.append(current)

    chunks: list[DomainChunk] = []
    for idx, text_part in enumerate(merged):
        full_with_header = f"{version.context_header}\n{text_part}"
        chunks.append(
            DomainChunk(
                chunk_id=f"{version.version_id}#c{idx}",
                parent_id=version.version_id,
                chunk_kind="norm",
                chunk_index=idx,
                context_header=version.context_header,
                content=text_part,
                embedding=embedder.embed_document(full_with_header),
            )
        )
    return chunks


def chunk_court_decision(
    decision: CourtDecision,
    *,
    embedder: EmbeddingAdapter,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[DomainChunk]:
    """Erstellt einen eigenen Chunk für den Leitsatz sowie überlappende Chunks für Tenor/Gründe."""
    header = (
        f"[{decision.court_name} | {decision.decision_date.isoformat()} | "
        f"{decision.file_number} | {decision.ecli}]"
    )
    chunks: list[DomainChunk] = []
    idx = 0
    if decision.leitsatz.strip():
        chunks.append(
            DomainChunk(
                chunk_id=f"{decision.decision_id}#leitsatz",
                parent_id=decision.decision_id,
                chunk_kind="leitsatz",
                chunk_index=idx,
                context_header=header,
                content=decision.leitsatz.strip(),
                embedding=embedder.embed_document(f"{header}\nLeitsatz: {decision.leitsatz.strip()}"),
            )
        )
        idx += 1

    if decision.tenor.strip():
        chunks.append(
            DomainChunk(
                chunk_id=f"{decision.decision_id}#tenor",
                parent_id=decision.decision_id,
                chunk_kind="tenor",
                chunk_index=idx,
                context_header=header,
                content=decision.tenor.strip(),
                embedding=embedder.embed_document(f"{header}\nTenor: {decision.tenor.strip()}"),
            )
        )
        idx += 1

    body = decision.full_text.strip()
    start = 0
    step = max(200, chunk_size - overlap)
    while start < len(body):
        snippet = body[start : start + chunk_size].strip()
        if snippet:
            chunks.append(
                DomainChunk(
                    chunk_id=f"{decision.decision_id}#r{idx}",
                    parent_id=decision.decision_id,
                    chunk_kind="reasoning",
                    chunk_index=idx,
                    context_header=header,
                    content=snippet,
                    embedding=embedder.embed_document(f"{header}\n{snippet}"),
                )
            )
            idx += 1
        start += step
    return chunks


@dataclass
class EmbeddingAdapter:
    """Adapter für Qwen3-Embedding-4B (MIRACL-German), BGE-M3, Ollama oder deterministischen Lokaltest."""

    settings: LexAuditSettings = field(default_factory=get_settings)

    def format_query(
        self,
        query: str,
        instruct: str = "Finde relevante deutsche und europäische Rechtsnormen und Urteile zur Anfrage.",
    ) -> str:
        """Qwen3-Embedding-4B erfordert auf Deutsch ein englisches Query-Instruct-Präfix."""
        if self.settings.embedding_provider == "qwen3-4b":
            return (
                f"Instruct: Retrieve German and EU legal norms and rulings matching: {instruct}\n"
                f"Query: {query}"
            )
        return query

    def embed_document(self, text: str) -> list[float]:
        return self._deterministic_vector(text, dim=self.settings.embedding_dim)

    def embed_query(self, query: str) -> list[float]:
        formatted = self.format_query(query)
        return self._deterministic_vector(formatted, dim=self.settings.embedding_dim)

    @staticmethod
    def _deterministic_vector(text: str, dim: int = 1024) -> list[float]:
        """Leichter deterministischer Sparse-Hashing-Vektor (Zeichen-Trigramme + Tokens) mit L2-Normierung."""
        vec = [0.0] * dim
        normalized = " ".join(text.lower().split())
        tokens = re.findall(r"[a-zäöüß0-9§]+", normalized)
        features = list(tokens)
        for tok in tokens:
            if len(tok) >= 3:
                features.extend(tok[i : i + 3] for i in range(len(tok) - 2))
        if not features:
            vec[0] = 1.0
            return vec
        for feat in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True))
