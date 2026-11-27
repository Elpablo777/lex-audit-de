"""Phase-4-Tests: StateLawConnector (16 Bundesländer), robots.txt-Schutz, DNG & NeuRIS-Guard."""

from __future__ import annotations

import pytest
from lexaudit_pipelines.connectors import (
    DeprecatedEndpointBlockedError,
    EURLexSPARQLConnector,
    NeuRISConnector,
    RobotsTxtBlockedError,
    RobotsTxtGuard,
)
from lexaudit_pipelines.state_connectors import (
    STATE_PORTAL_REGISTRY,
    DNGOpenDataRequestGenerator,
    get_state_connector,
)


def test_all_16_federal_states_registered_and_compliant() -> None:
    assert len(STATE_PORTAL_REGISTRY) == 16
    for code in [
        "NI", "BW", "BY", "BE", "BB", "HB", "HH", "HE",
        "MV", "NW", "RP", "SL", "SN", "ST", "SH", "TH",
    ]:
        connector = get_state_connector(code)
        assert connector.verify_compliance(check_remote_robots=False) is True
        assert "http" in connector.build_legal_deeplink("BauO")


def test_robots_guard_blocks_commercial_bulk_portals() -> None:
    guard = RobotsTxtGuard()
    with pytest.raises(RobotsTxtBlockedError):
        guard.check_url("https://voris.wolterskluwer-online.de/browse")
    with pytest.raises(RobotsTxtBlockedError):
        guard.check_url("https://beck-online.beck.de/Search")


def test_neuris_blocks_deprecated_case_law_endpoint() -> None:
    with pytest.raises(DeprecatedEndpointBlockedError):
        NeuRISConnector.validate_path("/v1/case-law")
    assert NeuRISConnector.validate_path("/v1/rechtsprechung") == "/v1/rechtsprechung"


def test_dng_request_generator_and_eurlex_pagination() -> None:
    dng = DNGOpenDataRequestGenerator.generate_dng_request("BB")
    assert "Datennutzungsgesetz (DNG)" in dng
    assert "Brandenburg" in dng

    sparql = EURLexSPARQLConnector().build_paginated_query(limit=50, offset=100)
    assert "LIMIT 50 OFFSET 100" in sparql
