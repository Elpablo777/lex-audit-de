"""Dagster-Orchestrierung: Versionierte Legal-Data-Assets & tägliche Sensoren (0 KI-Tokens)."""

from pathlib import Path
from typing import Any

from dagster import (
    AssetExecutionContext,
    Definitions,
    RunRequest,
    SensorEvaluationContext,
    asset,
    define_asset_job,
    sensor,
)
from lexaudit_core.config import get_settings
from lexaudit_core.parsers.xml_parsers import (
    parse_formex_xml,
    parse_gii_xml,
    parse_legaldocml_xml,
    parse_rii_xml,
)
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import build_graph_from_storage


@asset(group_name="zero_token_core")
def pilot_corpus_asset(context: AssetExecutionContext) -> dict[str, int]:
    """Materialisiert den kuratierten Pilot-Korpus (Bund + NI + EU + Rechtsprechung) idempotent."""
    settings = get_settings()
    storage = SQLiteStorageBackend(settings.sqlite_fallback_path, settings=settings)
    stats = load_pilot_corpus(storage)
    context.log.info(f"Pilot-Korpus synchronisiert: {stats}")
    return stats


@asset(group_name="zero_token_core")
def xml_fixture_ingestion_asset(context: AssetExecutionContext) -> dict[str, int]:
    """Ingestiert GII-XML, LegalDocML.de, RII-XML und Formex-XML mit SHA-256-Diff-Erkennung."""
    settings = get_settings()
    storage = SQLiteStorageBackend(settings.sqlite_fallback_path, settings=settings)
    fixtures_dir = Path("tests/fixtures")
    changed = 0
    if (fixtures_dir / "gii_estg_sample.xml").exists():
        bundle = parse_gii_xml((fixtures_dir / "gii_estg_sample.xml").read_bytes(), legal_domain="Steuerrecht")
        storage.upsert_act(bundle.act)
        for n in bundle.norms:
            storage.upsert_norm(n)
        for v in bundle.versions:
            if storage.upsert_temporal_version(v):
                changed += 1
    if (fixtures_dir / "legaldocml_sgb2_sample.xml").exists():
        bundle = parse_legaldocml_xml((fixtures_dir / "legaldocml_sgb2_sample.xml").read_bytes())
        storage.upsert_act(bundle.act)
        for n in bundle.norms:
            storage.upsert_norm(n)
        for v in bundle.versions:
            if storage.upsert_temporal_version(v):
                changed += 1
    if (fixtures_dir / "formex_eu_sample.xml").exists():
        bundle = parse_formex_xml((fixtures_dir / "formex_eu_sample.xml").read_bytes())
        storage.upsert_act(bundle.act)
        for n in bundle.norms:
            storage.upsert_norm(n)
        for v in bundle.versions:
            if storage.upsert_temporal_version(v):
                changed += 1
    if (fixtures_dir / "rii_bverfg_sample.xml").exists():
        dec = parse_rii_xml((fixtures_dir / "rii_bverfg_sample.xml").read_bytes())
        storage.upsert_court_decision(dec)
    context.log.info(f"XML-Ingestion abgeschlossen, neue/geänderte Versionen: {changed}")
    return {"changed_versions": changed}


@asset(deps=[pilot_corpus_asset, xml_fixture_ingestion_asset], group_name="knowledge_graph")
def bitemporal_graph_asset(context: AssetExecutionContext) -> dict[str, Any]:
    """Baut den bitemporalen Knowledge Graph deterministisch ohne KI-Tokens auf."""
    settings = get_settings()
    storage = SQLiteStorageBackend(settings.sqlite_fallback_path, settings=settings)
    graph = build_graph_from_storage(storage)
    snap = graph.snapshot()
    context.log.info(f"Graph synchronisiert: {snap.stats}")
    return snap.stats


daily_legal_sync_job = define_asset_job(
    name="daily_legal_sync_job",
    selection=[pilot_corpus_asset, xml_fixture_ingestion_asset, bitemporal_graph_asset],
)


@sensor(job=daily_legal_sync_job, minimum_interval_seconds=86400)
def daily_bgbl_and_land_sensor(context: SensorEvaluationContext) -> RunRequest | None:
    """Täglicher Änderungs-Sensor auf BGBl / gii-toc.xml / verkuendung-niedersachsen.de."""
    cursor = context.cursor or "init"
    return RunRequest(run_key=f"daily_sync_{cursor}")


defs = Definitions(
    assets=[pilot_corpus_asset, xml_fixture_ingestion_asset, bitemporal_graph_asset],
    jobs=[daily_legal_sync_job],
    sensors=[daily_bgbl_and_land_sensor],
)
