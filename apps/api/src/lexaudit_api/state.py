"""Laufzeit-Zustandscontainer für das FastAPI-Backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from lexaudit_analyzer.pipeline import AuditPipeline
from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.schemas import AuditRun, ConflictFinding
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import (
    GraphRepository,
    build_graph_from_storage,
    create_graph_repository,
)


@dataclass
class AppRuntime:
    settings: LexAuditSettings
    storage: SQLiteStorageBackend
    graph: GraphRepository
    corpus_stats: dict[str, int] = field(default_factory=dict)
    last_run: AuditRun | None = None
    findings: list[ConflictFinding] = field(default_factory=list)


def create_runtime(settings: LexAuditSettings | None = None, *, in_memory: bool = False) -> AppRuntime:
    cfg = settings or get_settings()
    db_target = ":memory:" if in_memory else cfg.sqlite_fallback_path
    storage = SQLiteStorageBackend(db_target, settings=cfg)
    stats = load_pilot_corpus(storage)
    graph = create_graph_repository(cfg)
    build_graph_from_storage(storage, repo=graph)

    pipeline = AuditPipeline(storage=storage, graph=graph, settings=cfg)
    run, findings, _ = pipeline.run_audit(as_of=date(2026, 11, 27), persist=True)
    return AppRuntime(
        settings=cfg,
        storage=storage,
        graph=graph,
        corpus_stats=stats,
        last_run=run,
        findings=findings,
    )
