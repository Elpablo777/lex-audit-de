"""Phase-3-API-Tests: FastAPI-Endpunkte, SSE-Streaming, Z3-Simulatoren, Petitionen, RDG & Zeitreise."""

from __future__ import annotations

from fastapi.testclient import TestClient
from lexaudit_api.main import create_app


def _client() -> TestClient:
    app = create_app(in_memory=True)
    return TestClient(app)


def test_health_findings_and_graph_time_travel() -> None:
    with _client() as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.json()["portal_url"] == "http://127.0.0.1:3000"
        assert root.json()["docs_url"] == "/docs"

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        h_data = health.json()
        assert h_data["status"] == "ok"
        assert h_data["verified_findings_count"] == 5
        assert h_data["bverfg_2025"]["success_rate"] == 0.0112

        findings = client.get("/api/v1/findings").json()
        assert len(findings) == 5
        assert all(f["verification_status"] == "VERIFIED" for f in findings)

        detail = client.get("/api/v1/findings/finding-ni-nitrat-47vwgo")
        assert detail.status_code == 200
        assert detail.json()["briefing"]["competent_court"].startswith("Niedersächsisches")

        g_2024 = client.get("/api/v1/graph", params={"as_of": "2024-06-01"}).json()
        g_2026 = client.get("/api/v1/graph", params={"as_of": "2026-11-27"}).json()
        ids_2024 = {n["id"] for n in g_2024["nodes"]}
        ids_2026 = {n["id"] for n in g_2026["nodes"]}
        assert "de:land:ni:nduenggewnpvo:p_2" not in ids_2024
        assert "de:land:ni:nduenggewnpvo:p_2" in ids_2026


def test_sse_audit_stream_and_z3_simulators() -> None:
    with _client() as client:
        sse = client.get("/api/v1/audits/stream")
        assert sse.status_code == 200
        assert "stufe_a_z3" in sse.text
        assert '"progress_pct": 100' in sse.text

        hh = client.get("/api/v1/z3/household", params={"rent": 900, "children": 2}).json()
        assert hh["z3_proof"]["satisfiable"] is True
        assert len(hh["curve"]) >= 20

        erb = client.get("/api/v1/z3/erbstg", params={"business_assets_mio": 150}).json()
        assert erb["z3_proof"]["satisfiable"] is True
        assert erb["selected_point"]["effective_tax_rate_pct"] < 5.0


def test_petition_validation_representatives_states_and_assistant() -> None:
    with _client() as client:
        bad = client.post(
            "/api/v1/actions/petition",
            json={
                "finding_id": "finding-sozial-transferentzug-107pct",
                "target_portal": "bundestag_petition",
                "custom_text": "Siehe https://example.org für weitere Infos.",
            },
        ).json()
        assert bad["validation_passed"] is False

        reps = client.get(
            "/api/v1/actions/representatives",
            params={"postal_code": "30159", "legal_domain": "Umweltrecht", "live": False},
        ).json()
        assert len(reps["representatives"]) >= 1

        states = client.get("/api/v1/states").json()
        assert len(states) == 16

        dng = client.post("/api/v1/states/BB/dng-request", json={}).json()
        assert "Datennutzungsgesetz" in dng["dng_request_text"]

        rdg_block = client.post(
            "/api/v1/assistant/query",
            json={
                "query": "Habe ich in meinem konkreten Fall Anspruch auf Wohngeld?",
                "mode": "mode_a_public_compass",
            },
        ).json()
        assert rdg_block["rdg_blocked"] is True

        copilot_forbidden = client.post(
            "/api/v1/assistant/query",
            json={
                "query": "Normkette § 13a ErbStG",
                "mode": "mode_b_research_copilot",
                "brao_supervised_confirmed": False,
            },
        )
        assert copilot_forbidden.status_code == 403
