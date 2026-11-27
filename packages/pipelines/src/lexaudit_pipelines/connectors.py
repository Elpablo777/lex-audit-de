"""Amtliche & offen lizenzierte Datenquellen-Konnektoren (Stand Nov 2026) inkl. robots.txt-Guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.llm_clients import create_tls_client
from lxml import etree


class RobotsTxtBlockedError(PermissionError):
    """Wird ausgelöst, wenn robots.txt (§ 44b Abs. 3 UrhG) einen automatisierten Zugriff untersagt."""


class DeprecatedEndpointBlockedError(ValueError):
    """Blockiert abgeschaltete Endpunkte (z. B. NeuRIS /v1/case-law -> HTTP 410)."""


@dataclass
class RobotsTxtGuard:
    """Prüft maschinenlesbare Nutzungsvorbehalte (robots.txt nach § 44b UrhG)."""

    user_agent: str = "LexAudit-DE-EU"
    _cache: dict[str, RobotFileParser] = field(default_factory=dict)

    _PROTECTED_BULK_DOMAINS: tuple[str, ...] = (
        "juris.de",
        "beck-online.beck.de",
        "voris.wolterskluwer-online.de",
    )

    def check_url(self, url: str, *, allow_robots_fetch: bool = False) -> bool:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        for blocked_domain in self._PROTECTED_BULK_DOMAINS:
            if host == blocked_domain or host.endswith(f".{blocked_domain}"):
                raise RobotsTxtBlockedError(
                    f"Geschützte kommerzielle Datenbank '{host}' (§§ 87a ff. UrhG): "
                    "Automatisiertes Bulk-Scraping ist gesperrt; nur Deep-Links zulässig."
                )

        if not allow_robots_fetch:
            return True

        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._cache:
            rp = RobotFileParser()
            robots_url = f"{origin}/robots.txt"
            try:
                with create_tls_client(timeout=6.0) as client:
                    resp = client.get(robots_url)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.parse(["User-agent: *", "Allow: /"])
            except Exception:
                rp.parse(["User-agent: *", "Allow: /"])
            self._cache[origin] = rp

        allowed = self._cache[origin].can_fetch(self.user_agent, url)
        if not allowed:
            raise RobotsTxtBlockedError(
                f"robots.txt untersagt automatisierten Abruf von '{url}' (§ 44b Abs. 3 UrhG)."
            )
        return True


class NeuRISConnector:
    """BMJ/DigitalService NeuRIS API (LegalDocML.de / Hydra JSON-LD, keyless, § 5 UrhG)."""

    BASE_URL = "https://testphase.rechtsinformationen.bund.de"

    @classmethod
    def validate_path(cls, path: str) -> str:
        if "/case-law" in path or "case-law" in path:
            raise DeprecatedEndpointBlockedError(
                "NeuRIS /v1/case-law wurde im Oktober 2026 mit HTTP 410 abgeschaltet! "
                "Nutze zwingend /v1/rechtsprechung."
            )
        return path

    def fetch_legislation(self, limit: int = 5, query: str | None = None) -> list[dict[str, Any]]:
        path = self.validate_path("/v1/legislation")
        params: dict[str, str | int] = {"limit": limit}
        if query:
            params["searchTerm"] = query
        with create_tls_client(timeout=12.0) as client:
            resp = client.get(f"{self.BASE_URL}{path}", params=params)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("item", m) for m in data.get("member", [])]

    def fetch_rechtsprechung(self, limit: int = 5, query: str | None = None) -> list[dict[str, Any]]:
        path = self.validate_path("/v1/rechtsprechung")
        params: dict[str, str | int] = {"limit": limit}
        if query:
            params["searchTerm"] = query
        with create_tls_client(timeout=12.0) as client:
            resp = client.get(f"{self.BASE_URL}{path}", params=params)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("item", m) for m in data.get("member", [])]


class GIIConnector:
    """Gesetze-im-Internet Master-TOC (tagesaktuelle XML-Übersicht)."""

    TOC_URL = "https://www.gesetze-im-internet.de/gii-toc.xml"

    def fetch_toc_entries(self, limit: int = 20) -> list[dict[str, str]]:
        with create_tls_client(timeout=15.0) as client:
            resp = client.get(self.TOC_URL)
            resp.raise_for_status()
            root = etree.fromstring(resp.content)
        entries: list[dict[str, str]] = []
        for item in root.findall(".//item")[:limit]:
            entries.append(
                {
                    "title": (item.findtext("title") or "").strip(),
                    "link": (item.findtext("link") or "").strip(),
                }
            )
        return entries


class RIIConnector:
    """Rechtsprechung-im-Internet Master-TOC (keyless XML)."""

    TOC_URL = "https://www.rechtsprechung-im-internet.de/rii-toc.xml"

    def fetch_recent_decisions(self, limit: int = 10) -> list[dict[str, str]]:
        with create_tls_client(timeout=15.0) as client:
            resp = client.get(self.TOC_URL)
            resp.raise_for_status()
            root = etree.fromstring(resp.content)
        items: list[dict[str, str]] = []
        for item in root.findall(".//item")[:limit]:
            items.append(
                {
                    "gericht": (item.findtext("gericht") or "").strip(),
                    "aktenzeichen": (item.findtext("aktenzeichen") or "").strip(),
                    "entsch_datum": (item.findtext("entsch-datum") or "").strip(),
                    "link": (item.findtext("link") or "").strip(),
                }
            )
        return items


class EURLexSPARQLConnector:
    """EUR-Lex CELLAR SPARQL-Client mit zwingender LIMIT/OFFSET-Paginierung (< 60s Timeout)."""

    ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"

    def build_paginated_query(self, *, sector: str = "3", limit: int = 25, offset: int = 0) -> str:
        safe_limit = min(max(1, limit), 100)
        safe_offset = max(0, offset)
        return (
            "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"
            "SELECT ?work ?celex ?date WHERE {\n"
            f'  ?work cdm:resource_legal_id_sector "{sector}" .\n'
            "  ?work cdm:resource_legal_id_celex ?celex .\n"
            "  OPTIONAL { ?work cdm:work_date_document ?date . }\n"
            f"}} LIMIT {safe_limit} OFFSET {safe_offset}"
        )

    def fetch_works(self, *, sector: str = "3", limit: int = 5, offset: int = 0) -> list[dict[str, str]]:
        sparql = self.build_paginated_query(sector=sector, limit=limit, offset=offset)
        with create_tls_client(timeout=20.0) as client:
            resp = client.get(
                self.ENDPOINT,
                params={"query": sparql, "format": "application/sparql-results+json"},
            )
            resp.raise_for_status()
            bindings = resp.json().get("results", {}).get("bindings", [])
        return [
            {
                "work": row.get("work", {}).get("value", ""),
                "celex": row.get("celex", {}).get("value", ""),
                "date": row.get("date", {}).get("value", ""),
            }
            for row in bindings
        ]


class NiedersachsenVerkuendungConnector:
    """Amtliche Niedersächsische Verkündungsplattform (verkuendung-niedersachsen.de)."""

    SEARCH_URL = "https://www.verkuendung-niedersachsen.de/api/search"

    def search(self, query_text: str = "Dünge", size: int = 10) -> list[dict[str, Any]]:
        payload = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["metaData.title", "metaData.short_title", "content"],
                            }
                        }
                    ]
                }
            },
        }
        with create_tls_client(timeout=12.0) as client:
            resp = client.post(self.SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        results: list[dict[str, Any]] = []
        for hit in hits:
            src = hit.get("_source", {})
            meta = src.get("metaData", {})
            results.append(
                {
                    "id": hit.get("_id", ""),
                    "title": meta.get("title") or src.get("title") or "Nds. Verkündungsblatt",
                    "gazette": meta.get("gazette") or "Nds. GVBl.",
                    "year": meta.get("year"),
                    "number": meta.get("number"),
                    "source_url": "https://www.verkuendung-niedersachsen.de/",
                }
            )
        return results


class AbgeordnetenwatchConnector:
    """Abgeordnetenwatch API v2 (CC0 1.0) für Parlamente, Mandate & Ausschüsse."""

    BASE_URL = "https://www.abgeordnetenwatch.de/api/v2"

    _FALLBACK_MANDATES: list[dict[str, Any]] = [
        {
            "politician": "Dr. Clara Muster (Beispiel-Abgeordnete Wahlkreis Hannover-Stadt)",
            "parliament": "Bundestag",
            "constituency": "Stadt Hannover I (Wahlkreis 41)",
            "committees": ["Finanzausschuss", "Ausschuss für Arbeit und Soziales"],
            "party": "Fraktionsübergreifend (Demo-Datensatz)",
            "profile_url": "https://www.abgeordnetenwatch.de/",
        },
        {
            "politician": "Henrik Beispiel (MdL Niedersachsen)",
            "parliament": "Landtag Niedersachsen",
            "constituency": "Hannover-Mitte / Region",
            "committees": ["Ausschuss für Umwelt, Energie und Klimaschutz", "Rechts- und Verfassungsausschuss"],
            "party": "Fraktionsübergreifend (Demo-Datensatz)",
            "profile_url": "https://www.abgeordnetenwatch.de/",
        },
    ]

    def fetch_parliaments(self, limit: int = 20) -> list[dict[str, Any]]:
        with create_tls_client(timeout=10.0) as client:
            resp = client.get(f"{self.BASE_URL}/parliaments", params={"range_end": limit})
            resp.raise_for_status()
            return list(resp.json().get("data", []))

    def lookup_representatives(
        self, *, postal_code: str, legal_domain: str, offline: bool = False
    ) -> list[dict[str, Any]]:
        """Ordnet PLZ/Rechtsgebiet sachlich zuständigen Mandaten & Ausschüssen zu (ohne Wahlempfehlung)."""
        if offline:
            return self._fallback_mandates_for(postal_code, legal_domain)
        try:
            parliaments = self.fetch_parliaments(limit=18)
            bt = next((p for p in parliaments if "Bundestag" in str(p.get("label", ""))), None)
            nds = next((p for p in parliaments if "Niedersachsen" in str(p.get("label", ""))), None)
            matches: list[dict[str, Any]] = []
            if bt:
                matches.append(
                    {
                        "politician": "Zuständiges Wahlkreis- & Ausschussbüro (Bundestag)",
                        "parliament": bt.get("label", "Bundestag"),
                        "constituency": f"PLZ-Bereich {postal_code}",
                        "committees": self._committees_for_domain(legal_domain),
                        "profile_url": "https://www.abgeordnetenwatch.de/bundestag",
                        "api_source": "abgeordnetenwatch.de/api/v2 (CC0 1.0, live)",
                    }
                )
            if nds or postal_code.startswith(("2", "3")):
                matches.append(
                    {
                        "politician": "Zuständiges Landtags- & Ausschussbüro (Niedersachsen)",
                        "parliament": nds.get("label", "Landtag Niedersachsen") if nds else "Landtag Niedersachsen",
                        "constituency": f"Niedersachsen PLZ {postal_code}",
                        "committees": self._committees_for_domain(legal_domain),
                        "profile_url": "https://www.abgeordnetenwatch.de/niedersachsen",
                        "api_source": "abgeordnetenwatch.de/api/v2 (CC0 1.0, live)",
                    }
                )
            return matches or self._fallback_mandates_for(postal_code, legal_domain)
        except Exception:
            return self._fallback_mandates_for(postal_code, legal_domain)

    @staticmethod
    def _committees_for_domain(legal_domain: str) -> list[str]:
        low = legal_domain.lower()
        if "steuer" in low or "erbst" in low:
            return ["Finanzausschuss", "Rechtsausschuss"]
        if "sozial" in low or "wohngeld" in low:
            return ["Ausschuss für Arbeit und Soziales", "Ausschuss für Wohnen und Bauwesen"]
        if "umwelt" in low or "klima" in low or "nitrat" in low:
            return ["Ausschuss für Umwelt, Naturschutz, nukleare Sicherheit", "Ausschuss für Ernährung und Landwirtschaft"]
        return ["Rechtsausschuss", "Petitionsausschuss"]

    def _fallback_mandates_for(self, postal_code: str, legal_domain: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in self._FALLBACK_MANDATES:
            copy = dict(item)
            copy["constituency"] = f"{item['constituency']} (PLZ {postal_code})"
            copy["committees"] = self._committees_for_domain(legal_domain)
            copy["api_source"] = "abgeordnetenwatch.de/api/v2 (Offline-Referenz)"
            out.append(copy)
        return out


class FragDenStaatConnector:
    """FragDenStaat API v1 für Behörden-Routing & DNG/IFG-Anfragen."""

    BASE_URL = "https://fragdenstaat.de/api/v1"

    def search_public_bodies(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        with create_tls_client(timeout=10.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/publicbody/",
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            return list(resp.json().get("objects", []))


class BundestagDIPConnector:
    """Bundestag DIP API v1 (dl-de/by-2-0) für Vorgänge & Gesetzesbegründungen."""

    BASE_URL = "https://search.dip.bundestag.de/api/v1"

    def __init__(self, settings: LexAuditSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def fetch_drucksachen(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.settings.bundestag_dip_api_key:
            return []
        with create_tls_client(timeout=12.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/drucksache",
                params={"q": query, "apikey": self.settings.bundestag_dip_api_key},
            )
            resp.raise_for_status()
            return list(resp.json().get("documents", []))[:limit]


class OpenLegalDataConnector:
    """Open Legal Data (de.openlegaldata.io, ODbL v1.0) für ~424.000 Instanzurteile."""

    BASE_URL = "https://de.openlegaldata.io/api"
    ATTRIBUTION = "Datenquelle: Open Legal Data (https://de.openlegaldata.io), Datenbanklizenz ODbL v1.0; Urteile gemeinfrei nach § 5 UrhG."

    def fetch_courts(self, state_name: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if state_name:
            params["state__name"] = state_name
        with create_tls_client(timeout=12.0) as client:
            resp = client.get(f"{self.BASE_URL}/courts/", params=params)
            resp.raise_for_status()
            results = list(resp.json().get("results", []))
        for r in results:
            r["attribution"] = self.ATTRIBUTION
        return results

    def fetch_cases(self, court_id: int | None = None, limit: int = 5) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if court_id is not None:
            params["court"] = court_id
        with create_tls_client(timeout=12.0) as client:
            resp = client.get(f"{self.BASE_URL}/cases/", params=params)
            resp.raise_for_status()
            results = list(resp.json().get("results", []))
        for r in results:
            r["attribution"] = self.ATTRIBUTION
        return results


class HUDOCConnector:
    """EGMR HUDOC Keyless API + HUDOC-EXEC Umsetzungsstatus gegen Deutschland."""

    QUERY_URL = "https://hudoc.echr.coe.int/app/query/results"

    def search_germany_judgments(self, limit: int = 5) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "query": 'contentsitename:ECHR AND respondent:"DEU"',
            "select": "itemid,docname,ecli,kpdate,importance,conclusion",
            "sort": "kpdate Descending",
            "start": 0,
            "length": limit,
        }
        with create_tls_client(timeout=15.0) as client:
            resp = client.get(self.QUERY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        out: list[dict[str, Any]] = []
        for item in data.get("results", []):
            cols = item.get("columns", {})
            itemid = cols.get("itemid", "")
            out.append(
                {
                    "itemid": itemid,
                    "docname": cols.get("docname", ""),
                    "ecli": cols.get("ecli", ""),
                    "kpdate": cols.get("kpdate", ""),
                    "conclusion": cols.get("conclusion", ""),
                    "hudoc_url": f"https://hudoc.echr.coe.int/eng?i={itemid}",
                    "hudoc_exec_url": f"https://hudoc.exec.coe.int/eng?i={itemid}",
                }
            )
        return out
