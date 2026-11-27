"""Hybrid-Speicherschicht (PostgreSQL 17 + pgvector mit ef_search=200 sowie SQLite-FTS5-Fallback)."""

from __future__ import annotations

import functools
import json
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.embeddings import DomainChunk, EmbeddingAdapter, cosine_similarity
from lexaudit_core.schemas import (
    AuditRun,
    ComponentTemporalVersion,
    ConflictFinding,
    CourtDecision,
    LegalAct,
    NormUnit,
    ParliamentaryDoc,
    TemporalStatus,
)


def _synchronized[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """Serialisiert SQLite-Zugriffe sauber über den Instanz-RLock für Multi-Thread-APIs."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        self_obj: Any = args[0]
        lock: threading.RLock = self_obj._lock
        with lock:
            return fn(*args, **kwargs)

    return wrapper


@dataclass(frozen=True)
class SearchHit:
    item_id: str
    item_kind: str
    context_header: str
    content: str
    score: float
    source_url: str


class StorageBackend(Protocol):
    def upsert_act(self, act: LegalAct) -> None: ...
    def upsert_norm(self, norm: NormUnit) -> None: ...
    def upsert_temporal_version(self, version: ComponentTemporalVersion) -> bool: ...
    def upsert_court_decision(self, decision: CourtDecision) -> None: ...
    def upsert_parliamentary_doc(self, doc: ParliamentaryDoc) -> None: ...
    def upsert_chunks(self, chunks: list[DomainChunk]) -> None: ...
    def get_act(self, act_id: str) -> LegalAct | None: ...
    def get_norm(self, norm_id: str) -> NormUnit | None: ...
    def list_norms(self, limit: int = 500) -> list[NormUnit]: ...
    def list_acts(self) -> list[LegalAct]: ...
    def list_court_decisions(self) -> list[CourtDecision]: ...
    def list_parliamentary_docs(self) -> list[ParliamentaryDoc]: ...
    def get_version_at_date(
        self, norm_id: str, as_of: date | None = None
    ) -> ComponentTemporalVersion | None: ...
    def list_versions_for_norm(self, norm_id: str) -> list[ComponentTemporalVersion]: ...
    def lookup_full_text(
        self, ref_id: str, as_of: date | None = None
    ) -> tuple[str, str, str, str] | None: ...
    @_synchronized
    def hybrid_search(self, query: str, *, limit: int = 10) -> list[SearchHit]: ...
    def save_finding(self, finding: ConflictFinding) -> None: ...
    def get_finding(self, finding_id: str) -> ConflictFinding | None: ...
    def list_findings(self, include_rejected: bool = False) -> list[ConflictFinding]: ...
    def save_audit_run(self, run: AuditRun) -> None: ...
    def list_audit_runs(self, limit: int = 20) -> list[AuditRun]: ...


class SQLiteStorageBackend:
    """Vertragstreuer lokaler Speicher mit SQLite FTS5, bitemporaler Historie & Vektor-Suche."""

    def __init__(self, db_path: str | Path = ":memory:", settings: LexAuditSettings | None = None) -> None:
        self.db_path = str(db_path)
        self.settings = settings or get_settings()
        self.embedder = EmbeddingAdapter(self.settings)
        self._lock = threading.RLock()
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS legal_acts (
                act_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS norm_units (
                norm_id TEXT PRIMARY KEY,
                act_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS temporal_versions (
                version_id TEXT PRIMARY KEY,
                norm_id TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT,
                status TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS court_decisions (
                decision_id TEXT PRIMARY KEY,
                ecli TEXT UNIQUE NOT NULL,
                decision_date TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS parliamentary_docs (
                doc_id TEXT PRIMARY KEY,
                publication_date TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                chunk_kind TEXT NOT NULL,
                context_header TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                source_url TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                context_header,
                content
            );
            CREATE TABLE IF NOT EXISTS conflict_findings (
                finding_id TEXT PRIMARY KEY,
                verification_status TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    @_synchronized
    def upsert_act(self, act: LegalAct) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO legal_acts (act_id, payload) VALUES (?, ?)",
            (act.act_id, act.model_dump_json()),
        )
        self._conn.commit()

    @_synchronized
    def upsert_norm(self, norm: NormUnit) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO norm_units (norm_id, act_id, payload) VALUES (?, ?, ?)",
            (norm.norm_id, norm.act_id, norm.model_dump_json()),
        )
        self._conn.commit()

    @_synchronized
    def upsert_temporal_version(self, version: ComponentTemporalVersion) -> bool:
        """Legt neue bitemporale Fassung an, ohne alte Fassungen zu überschreiben.

        Gibt True zurück, wenn sich der Inhalt (text_hash) geändert hat oder neu ist.
        """
        existing = self._conn.execute(
            "SELECT version_id, text_hash, payload FROM temporal_versions "
            "WHERE norm_id = ? ORDER BY valid_from DESC",
            (version.norm_id,),
        ).fetchall()

        if any(row["text_hash"] == version.text_hash and row["version_id"] == version.version_id for row in existing):
            return False

        latest = existing[0] if existing else None
        supersedes_id = version.supersedes_version_id
        if latest is not None and latest["text_hash"] != version.text_hash:
            supersedes_id = supersedes_id or str(latest["version_id"])
            old_obj = ComponentTemporalVersion.model_validate_json(latest["payload"])
            if old_obj.valid_to is None and version.valid_from > old_obj.valid_from:
                old_obj = old_obj.model_copy(
                    update={"valid_to": version.valid_from, "status": TemporalStatus.REPEALED}
                )
                self._conn.execute(
                    "UPDATE temporal_versions SET valid_to = ?, status = ?, payload = ? WHERE version_id = ?",
                    (
                        old_obj.valid_to.isoformat() if old_obj.valid_to else None,
                        old_obj.status.value,
                        old_obj.model_dump_json(),
                        old_obj.version_id,
                    ),
                )

        to_store = version.model_copy(update={"supersedes_version_id": supersedes_id})
        self._conn.execute(
            "INSERT OR REPLACE INTO temporal_versions "
            "(version_id, norm_id, valid_from, valid_to, status, text_hash, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                to_store.version_id,
                to_store.norm_id,
                to_store.valid_from.isoformat(),
                to_store.valid_to.isoformat() if to_store.valid_to else None,
                to_store.status.value,
                to_store.text_hash,
                to_store.model_dump_json(),
            ),
        )
        self._conn.commit()
        return True

    @_synchronized
    def upsert_court_decision(self, decision: CourtDecision) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO court_decisions (decision_id, ecli, decision_date, payload) "
            "VALUES (?, ?, ?, ?)",
            (
                decision.decision_id,
                decision.ecli,
                decision.decision_date.isoformat(),
                decision.model_dump_json(),
            ),
        )
        self._conn.commit()

    @_synchronized
    def upsert_parliamentary_doc(self, doc: ParliamentaryDoc) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO parliamentary_docs (doc_id, publication_date, payload) "
            "VALUES (?, ?, ?)",
            (doc.doc_id, doc.publication_date.isoformat(), doc.model_dump_json()),
        )
        self._conn.commit()

    @_synchronized
    def upsert_chunks(self, chunks: list[DomainChunk], source_url: str = "") -> None:
        for ch in chunks:
            self._conn.execute(
                "INSERT OR REPLACE INTO chunks "
                "(chunk_id, parent_id, chunk_kind, context_header, content, embedding_json, source_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ch.chunk_id,
                    ch.parent_id,
                    ch.chunk_kind,
                    ch.context_header,
                    ch.content,
                    json.dumps(ch.embedding),
                    source_url,
                ),
            )
            self._conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (ch.chunk_id,))
            self._conn.execute(
                "INSERT INTO chunks_fts (chunk_id, context_header, content) VALUES (?, ?, ?)",
                (ch.chunk_id, ch.context_header, ch.content),
            )
        self._conn.commit()

    @_synchronized
    def get_act(self, act_id: str) -> LegalAct | None:
        row = self._conn.execute("SELECT payload FROM legal_acts WHERE act_id = ?", (act_id,)).fetchone()
        return LegalAct.model_validate_json(row["payload"]) if row else None

    @_synchronized
    def get_norm(self, norm_id: str) -> NormUnit | None:
        row = self._conn.execute("SELECT payload FROM norm_units WHERE norm_id = ?", (norm_id,)).fetchone()
        return NormUnit.model_validate_json(row["payload"]) if row else None

    @_synchronized
    def list_norms(self, limit: int = 500) -> list[NormUnit]:
        rows = self._conn.execute("SELECT payload FROM norm_units LIMIT ?", (limit,)).fetchall()
        return [NormUnit.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def list_acts(self) -> list[LegalAct]:
        rows = self._conn.execute("SELECT payload FROM legal_acts").fetchall()
        return [LegalAct.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def list_court_decisions(self) -> list[CourtDecision]:
        rows = self._conn.execute(
            "SELECT payload FROM court_decisions ORDER BY decision_date DESC"
        ).fetchall()
        return [CourtDecision.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def list_parliamentary_docs(self) -> list[ParliamentaryDoc]:
        rows = self._conn.execute(
            "SELECT payload FROM parliamentary_docs ORDER BY publication_date DESC"
        ).fetchall()
        return [ParliamentaryDoc.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def get_version_at_date(
        self, norm_id: str, as_of: date | None = None
    ) -> ComponentTemporalVersion | None:
        target = (as_of or date.today()).isoformat()
        rows = self._conn.execute(
            "SELECT payload FROM temporal_versions WHERE norm_id = ? "
            "AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?) "
            "ORDER BY valid_from DESC LIMIT 1",
            (norm_id, target, target),
        ).fetchall()
        if rows:
            return ComponentTemporalVersion.model_validate_json(rows[0]["payload"])
        fallback = self._conn.execute(
            "SELECT payload FROM temporal_versions WHERE norm_id = ? ORDER BY valid_from DESC LIMIT 1",
            (norm_id,),
        ).fetchone()
        return ComponentTemporalVersion.model_validate_json(fallback["payload"]) if fallback else None

    @_synchronized
    def list_versions_for_norm(self, norm_id: str) -> list[ComponentTemporalVersion]:
        rows = self._conn.execute(
            "SELECT payload FROM temporal_versions WHERE norm_id = ? ORDER BY valid_from ASC",
            (norm_id,),
        ).fetchall()
        return [ComponentTemporalVersion.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def lookup_full_text(
        self, ref_id: str, as_of: date | None = None
    ) -> tuple[str, str, str, str] | None:
        """Liefert (volltext, source_url, eli_oder_ecli, status) direkt aus dem Spiegel (nie nur Snippets!)."""
        norm = self.get_norm(ref_id)
        if norm:
            ver = self.get_version_at_date(norm.norm_id, as_of=as_of)
            act = self.get_act(norm.act_id)
            if ver and act:
                return (
                    ver.full_text,
                    act.source_url,
                    norm.eli_uri or act.eli_uri or norm.norm_id,
                    ver.status.value,
                )

        row = self._conn.execute(
            "SELECT payload FROM court_decisions WHERE decision_id = ? OR ecli = ?",
            (ref_id, ref_id),
        ).fetchone()
        if row:
            dec = CourtDecision.model_validate_json(row["payload"])
            return dec.full_text, dec.source_url, dec.ecli, "in_force"

        doc_row = self._conn.execute(
            "SELECT payload FROM parliamentary_docs WHERE doc_id = ? OR payload LIKE ?",
            (ref_id, f'%"{ref_id}"%'),
        ).fetchone()
        if doc_row:
            doc = ParliamentaryDoc.model_validate_json(doc_row["payload"])
            return f"{doc.title}\n{doc.summary}", doc.source_url, doc.doc_number, "in_force"
        return None

    @_synchronized
    def hybrid_search(self, query: str, *, limit: int = 10) -> list[SearchHit]:
        """Kombiniert Vektor-Kosinusähnlichkeit mit SQLite-FTS5-Keywords."""
        q_vec = self.embedder.embed_query(query)
        fts_terms = [t for t in query.replace("§", " ").split() if len(t) >= 2][:6]
        fts_scores: dict[str, float] = {}
        if fts_terms:
            fts_query = " OR ".join(f'"{t.replace(chr(34), "")}"' for t in fts_terms)
            try:
                fts_rows = self._conn.execute(
                    "SELECT chunk_id, bm25(chunks_fts) AS rank FROM chunks_fts WHERE chunks_fts MATCH ? LIMIT 50",
                    (fts_query,),
                ).fetchall()
                for r in fts_rows:
                    fts_scores[str(r["chunk_id"])] = 1.0 / (1.0 + abs(float(r["rank"])))
            except sqlite3.OperationalError:
                pass

        rows = self._conn.execute(
            "SELECT chunk_id, parent_id, chunk_kind, context_header, content, embedding_json, source_url FROM chunks"
        ).fetchall()
        scored: list[SearchHit] = []
        for r in rows:
            vec = json.loads(r["embedding_json"])
            cos = cosine_similarity(q_vec, vec)
            kw = fts_scores.get(str(r["chunk_id"]), 0.0)
            combined = 0.65 * cos + 0.35 * kw
            scored.append(
                SearchHit(
                    item_id=str(r["parent_id"]),
                    item_kind=str(r["chunk_kind"]),
                    context_header=str(r["context_header"]),
                    content=str(r["content"]),
                    score=round(combined, 4),
                    source_url=str(r["source_url"]),
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]

    @_synchronized
    def save_finding(self, finding: ConflictFinding) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO conflict_findings (finding_id, verification_status, payload) "
            "VALUES (?, ?, ?)",
            (finding.finding_id, finding.verification_status.value, finding.model_dump_json()),
        )
        self._conn.commit()

    @_synchronized
    def get_finding(self, finding_id: str) -> ConflictFinding | None:
        row = self._conn.execute(
            "SELECT payload FROM conflict_findings WHERE finding_id = ?", (finding_id,)
        ).fetchone()
        return ConflictFinding.model_validate_json(row["payload"]) if row else None

    @_synchronized
    def list_findings(self, include_rejected: bool = False) -> list[ConflictFinding]:
        if include_rejected:
            rows = self._conn.execute("SELECT payload FROM conflict_findings").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT payload FROM conflict_findings WHERE verification_status = 'VERIFIED'"
            ).fetchall()
        return [ConflictFinding.model_validate_json(r["payload"]) for r in rows]

    @_synchronized
    def save_audit_run(self, run: AuditRun) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO audit_runs (run_id, started_at, payload) VALUES (?, ?, ?)",
            (run.run_id, run.started_at.isoformat(), run.model_dump_json()),
        )
        self._conn.commit()

    @_synchronized
    def list_audit_runs(self, limit: int = 20) -> list[AuditRun]:
        rows = self._conn.execute(
            "SELECT payload FROM audit_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [AuditRun.model_validate_json(r["payload"]) for r in rows]


class PostgresVectorStorageBackend:
    """PostgreSQL 17 + pgvector Produktions-Backend mit zwingendem `SET LOCAL hnsw.ef_search = 200;`."""

    def __init__(self, dsn: str, settings: LexAuditSettings | None = None) -> None:
        self.dsn = dsn.replace("postgresql+psycopg://", "postgresql://")
        self.settings = settings or get_settings()
        self.embedder = EmbeddingAdapter(self.settings)

    def _connect(self) -> Any:
        import psycopg

        return psycopg.connect(self.dsn)

    def vector_search_norm_chunks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Führt eine pgvector-HNSW-Abfrage mit garantiertem ef_search=200 aus."""
        q_vec = self.embedder.embed_query(query)
        vec_literal = "[" + ",".join(str(x) for x in q_vec) + "]"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(f"SET LOCAL hnsw.ef_search = {int(self.settings.hnsw_ef_search)};")
            cur.execute(
                """
                SELECT chunk_id, norm_id, context_header, content,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM norm_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (vec_literal, vec_literal, limit),
            )
            cols = [desc[0] for desc in cur.description or []]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
