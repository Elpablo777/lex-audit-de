"""Dagster-Definitions- & Materialisierungs-Test."""

from __future__ import annotations

from pathlib import Path

import pytest
from dagster import materialize
from lexaudit_core.config import get_settings
from lexaudit_pipelines.definitions import (
    bitemporal_graph_asset,
    defs,
    pilot_corpus_asset,
    xml_fixture_ingestion_asset,
)


def test_dagster_definitions_materialize_zero_token_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_file = tmp_path / "dagster_test.sqlite3"
    monkeypatch.setenv("LEXAUDIT_SQLITE_PATH", str(db_file))
    get_settings.cache_clear()
    try:
        assert defs.resolve_all_job_defs()
        result = materialize(
            [pilot_corpus_asset, xml_fixture_ingestion_asset, bitemporal_graph_asset]
        )
        assert result.success
        stats = result.output_for_node("bitemporal_graph_asset")
        assert stats["nodes"] >= 15
        assert stats["edges"] >= 5
    finally:
        get_settings.cache_clear()
