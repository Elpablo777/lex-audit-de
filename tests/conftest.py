"""Gemeinsame Pytest-Konfiguration inkl. `--strict-citations` Gate für tests/eval/."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--strict-citations",
        action="store_true",
        default=False,
        help="Erzwingt 100 % verifizierte Zitationen und alle RAGAS-Produktiv-Schwellenwerte.",
    )
