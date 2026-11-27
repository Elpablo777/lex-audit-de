"""Phase-1-Unit-Tests: XML-Parser, QuantLaw-Referenzparser, bitemporale Historie, Hybrid-Search & Graph."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from lexaudit_core.config import LexAuditSettings
from lexaudit_core.embeddings import EmbeddingAdapter
from lexaudit_core.parsers.reference_parser import QuantLawReferenceParser
from lexaudit_core.parsers.xml_parsers import (
    compute_text_hash,
    parse_formex_xml,
    parse_gii_xml,
    parse_legaldocml_xml,
    parse_rii_xml,
)
from lexaudit_core.schemas import ComponentTemporalVersion, TemporalStatus
from lexaudit_core.seed_corpus import load_pilot_corpus
from lexaudit_core.storage import SQLiteStorageBackend
from lexaudit_graph.repository import build_graph_from_storage


def test_xml_parsers_extract_gii_legaldocml_rii_and_formex() -> None:
    fx = Path("tests/fixtures")

    gii = parse_gii_xml((fx / "gii_estg_sample.xml").read_bytes(), legal_domain="Steuerrecht")
    assert gii.act.short_title == "ErbStG"
    assert len(gii.norms) == 2
    assert "26 Millionen Euro" in gii.versions[0].full_text

    akn = parse_legaldocml_xml((fx / "legaldocml_sgb2_sample.xml").read_bytes())
    assert akn.norms[0].designation == "§ 11b"
    assert "Transferentzugsraten" in akn.versions[0].full_text

    dec = parse_rii_xml((fx / "rii_bverfg_sample.xml").read_bytes())
    assert dec.ecli == "ECLI:DE:BVERFG:2021:rs20210324.1bvr265618"
    assert "intertemporale Freiheitssicherung" in dec.leitsatz

    eu = parse_formex_xml((fx / "formex_eu_sample.xml").read_bytes())
    assert eu.transposition_deadline == date(1993, 12, 20)
    assert eu.norms[0].designation == "Artikel 5"


def test_quantlaw_reference_parser_handles_complex_german_citations() -> None:
    parser = QuantLawReferenceParser()
    text = (
        "Nach § 11b Abs. 3 SGB II in Verbindung mit § 19 WoGG und §§ 823 bis 825 BGB "
        "sowie zur Umsetzung der Richtlinie 91/676/EWG."
    )
    known = {
        "de:bund:sgb2:p_11b",
        "de:bund:wogg:p_19",
        "de:bund:bgb:p_823",
        "de:bund:bgb:p_824",
        "de:bund:bgb:p_825",
    }
    refs = parser.extract_references(
        text,
        src_norm_id="de:bund:bkgg:p_6a",
        default_law_prefix="de:bund:bkgg",
        known_norm_ids=known,
    )
    tgts = {r.tgt_norm_id for r in refs}
    assert "de:bund:sgb2:p_11b" in tgts
    assert "de:bund:wogg:p_19" in tgts
    assert {"de:bund:bgb:p_823", "de:bund:bgb:p_824", "de:bund:bgb:p_825"} <= tgts
    assert "eu:dir:91_676_ewg" in tgts
    assert any(r.relation_type == "CONDITION_FOR" for r in refs)


def test_bitemporal_versioning_and_time_travel_graph() -> None:
    storage = SQLiteStorageBackend(":memory:")
    stats = load_pilot_corpus(storage)
    assert stats["norms"] >= 18

    # Neue Fassung für § 13a darf alte Versionen nicht überschreiben
    new_text = "(1) Aktualisierte Fassung 2027 nach BVerfG-Urteil."
    new_ver = ComponentTemporalVersion(
        version_id=f"de:bund:erbstg:p_13a@2027-03-01:{compute_text_hash(new_text)[:8]}",
        norm_id="de:bund:erbstg:p_13a",
        valid_from=date(2027, 3, 1),
        valid_to=None,
        promulgation_date=date(2027, 2, 15),
        status=TemporalStatus.IN_FORCE,
        text_hash=compute_text_hash(new_text),
        full_text=new_text,
        context_header="[ErbStG | § 13a | Fassung 2027]",
    )
    changed = storage.upsert_temporal_version(new_ver)
    assert changed is True
    versions = storage.list_versions_for_norm("de:bund:erbstg:p_13a")
    assert len(versions) == 3

    # Zeitreise zum Stichtag 2024-06-01 liefert historische 2016er Fassung
    hist = storage.get_version_at_date("de:bund:erbstg:p_13a", as_of=date(2024, 6, 1))
    assert hist is not None
    assert "historische Übergangsfassung" in hist.full_text

    # Graph-Zeitreise vor Inkrafttreten der NDüngGewNPVO,NI (2026-05-15) blendet 2026er VO aus
    graph = build_graph_from_storage(storage)
    snap_2024 = graph.snapshot(as_of=date(2024, 6, 1))
    snap_2026 = graph.snapshot(as_of=date(2026, 11, 27))
    ids_2024 = {n.id for n in snap_2024.nodes}
    ids_2026 = {n.id for n in snap_2026.nodes}
    assert "de:land:ni:nduenggewnpvo:p_2" not in ids_2024
    assert "de:land:ni:nduenggewnpvo:p_2" in ids_2026


def test_embedding_prefix_for_qwen3_and_hybrid_search() -> None:
    qwen = EmbeddingAdapter(LexAuditSettings(LEXAUDIT_EMBEDDING_PROVIDER="qwen3-4b"))
    formatted = qwen.format_query("Art. 1 GG")
    assert formatted.startswith("Instruct:")
    assert "Query: Art. 1 GG" in formatted

    storage = SQLiteStorageBackend(":memory:")
    load_pilot_corpus(storage)
    hits = storage.hybrid_search("Transferentzugsraten Wohngeld SGB II", limit=5)
    assert hits
    assert any("sgb2" in h.item_id or "wogg" in h.item_id for h in hits)
