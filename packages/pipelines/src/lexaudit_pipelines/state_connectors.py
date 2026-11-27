"""Föderale 16-Bundesländer StateLawConnector-Architektur inkl. § 44b/§ 87a UrhG-Schutz & DNG-Generator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from lexaudit_pipelines.connectors import RobotsTxtGuard


class StatePortalDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    land_code: str
    land_name: str
    portal_type: Literal["verkuendungsblatt", "juris_bsxx", "eigenportal", "wolters_kluwer"]
    official_portal_url: str
    gazette_url: str
    machine_readable_status: Literal["open_api", "robots_checked_limited", "protected_deeplink_only"]
    notes: str


STATE_PORTAL_REGISTRY: dict[str, StatePortalDescriptor] = {
    "NI": StatePortalDescriptor(
        land_code="NI",
        land_name="Niedersachsen (Pilot)",
        portal_type="verkuendungsblatt",
        official_portal_url="https://voris.wolterskluwer-online.de/",
        gazette_url="https://www.verkuendung-niedersachsen.de/",
        machine_readable_status="open_api",
        notes="Primärquelle amtliches E-GVBl/MBl (seit 2024); NI-VORIS nur Deep-Link (§ 87a UrhG).",
    ),
    "BW": StatePortalDescriptor(
        land_code="BW",
        land_name="Baden-Württemberg",
        portal_type="juris_bsxx",
        official_portal_url="https://www.landesrecht-bw.de/bsbw/search",
        gazette_url="https://www.verkuendung-bw.de/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsbw); robots.txt-Guard Pflicht.",
    ),
    "BY": StatePortalDescriptor(
        land_code="BY",
        land_name="Bayern",
        portal_type="eigenportal",
        official_portal_url="https://www.gesetze-bayern.de/",
        gazette_url="https://www.verkuendung-bayern.de/",
        machine_readable_status="robots_checked_limited",
        notes="BAYERN.RECHT (Gesetze, VO, VV, Rechtsprechung).",
    ),
    "BE": StatePortalDescriptor(
        land_code="BE",
        land_name="Berlin",
        portal_type="juris_bsxx",
        official_portal_url="https://gesetze.berlin.de/bsbe/search",
        gazette_url="https://www.berlin.de/sen/justva/service/gesetz-und-verordnungsblatt/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsbe).",
    ),
    "BB": StatePortalDescriptor(
        land_code="BB",
        land_name="Brandenburg",
        portal_type="eigenportal",
        official_portal_url="https://bravors.brandenburg.de/",
        gazette_url="https://bravors.brandenburg.de/",
        machine_readable_status="protected_deeplink_only",
        notes="BRAVORS blockiert automatisierte Crawler häufig; DNG-Open-Data-Antrag vorgesehen.",
    ),
    "HB": StatePortalDescriptor(
        land_code="HB",
        land_name="Bremen",
        portal_type="eigenportal",
        official_portal_url="https://www.transparenz.bremen.de/",
        gazette_url="https://www.gesetzblatt.bremen.de/",
        machine_readable_status="open_api",
        notes="Justizportal Bremen / Transparenzportal mit offenem Gesetzesblatt.",
    ),
    "HH": StatePortalDescriptor(
        land_code="HH",
        land_name="Hamburg",
        portal_type="juris_bsxx",
        official_portal_url="https://www.landesrecht-hamburg.de/bsha/search",
        gazette_url="https://www.luewu.de/gvbl/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsha).",
    ),
    "HE": StatePortalDescriptor(
        land_code="HE",
        land_name="Hessen",
        portal_type="juris_bsxx",
        official_portal_url="https://www.lareda.hessenrecht.hessen.de/bshe/search",
        gazette_url="https://starweb.hessen.de/cache/hessen/gvbl.htm",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bshe / LaReDa).",
    ),
    "MV": StatePortalDescriptor(
        land_code="MV",
        land_name="Mecklenburg-Vorpommern",
        portal_type="juris_bsxx",
        official_portal_url="https://www.landesrecht-mv.de/bsmv/search",
        gazette_url="https://www.regierung-mv.de/Landesregierung/jm/Service/Gesetz-und-Verordnungsblatt/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsmv).",
    ),
    "NW": StatePortalDescriptor(
        land_code="NW",
        land_name="Nordrhein-Westfalen",
        portal_type="eigenportal",
        official_portal_url="https://recht.nrw.de/",
        gazette_url="https://recht.nrw.de/lmi/owa/br_gvbl",
        machine_readable_status="protected_deeplink_only",
        notes="Eigenportal RECHT.NRW inkl. GVBl. & MBl.; Crawler-Sperren beachten.",
    ),
    "RP": StatePortalDescriptor(
        land_code="RP",
        land_name="Rheinland-Pfalz",
        portal_type="juris_bsxx",
        official_portal_url="https://www.landesrecht.rlp.de/bsrp/search",
        gazette_url="https://www.rlp.de/service/recht",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsrp).",
    ),
    "SL": StatePortalDescriptor(
        land_code="SL",
        land_name="Saarland",
        portal_type="eigenportal",
        official_portal_url="https://www.saarland.de/fgds/DE/landesrecht",
        gazette_url="https://www.amtsblatt.saarland.de/",
        machine_readable_status="robots_checked_limited",
        notes="Landesportal Saarland & elektronisches Amtsblatt.",
    ),
    "SN": StatePortalDescriptor(
        land_code="SN",
        land_name="Sachsen",
        portal_type="eigenportal",
        official_portal_url="https://www.revosax.sachsen.de/",
        gazette_url="https://www.revosax.sachsen.de/verkuendung",
        machine_readable_status="robots_checked_limited",
        notes="Eigenportal REVOSax.",
    ),
    "ST": StatePortalDescriptor(
        land_code="ST",
        land_name="Sachsen-Anhalt",
        portal_type="juris_bsxx",
        official_portal_url="https://www.landesrecht.sachsen-anhalt.de/bsst/search",
        gazette_url="https://padoka.landtag.sachsen-anhalt.de/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsst).",
    ),
    "SH": StatePortalDescriptor(
        land_code="SH",
        land_name="Schleswig-Holstein",
        portal_type="juris_bsxx",
        official_portal_url="https://www.gesetze-rechtsprechung.sh.juris.de/jportal/portal/page/bsshoprod.psml",
        gazette_url="https://www.schleswig-holstein.de/DE/landesregierung/themen/justiz/gesetz-verordnungsblatt/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Portal (bsshoprod).",
    ),
    "TH": StatePortalDescriptor(
        land_code="TH",
        land_name="Thüringen",
        portal_type="juris_bsxx",
        official_portal_url="https://landesrecht.thueringen.de/bsth/search",
        gazette_url="https://www.thueringen.de/th4/justiz/gesetzblatt/",
        machine_readable_status="robots_checked_limited",
        notes="juris-basiertes Landesportal (bsth).",
    ),
}


class StateLawConnector(ABC):
    """Gemeinsames Plugin-Interface für alle 16 Bundesländer."""

    def __init__(self, descriptor: StatePortalDescriptor, robots_guard: RobotsTxtGuard | None = None) -> None:
        self.descriptor = descriptor
        self.robots_guard = robots_guard or RobotsTxtGuard()

    @abstractmethod
    def build_legal_deeplink(self, abbreviation: str) -> str: ...

    def verify_compliance(self, *, check_remote_robots: bool = False) -> bool:
        return self.robots_guard.check_url(
            self.descriptor.gazette_url, allow_robots_fetch=check_remote_robots
        )


class VerkuendungsblattConnector(StateLawConnector):
    """Konnektor für amtliche elektronische Verkündungsblätter (§ 5 Abs. 1 UrhG)."""

    def build_legal_deeplink(self, abbreviation: str) -> str:
        return f"{self.descriptor.gazette_url}?q={abbreviation}"


class BsXXJurisConnector(StateLawConnector):
    """Gemeinsamer Konnektor für die 9 juris-basierten Landesportale (BW/BE/HH/HE/MV/RP/ST/SH/TH)."""

    def build_legal_deeplink(self, abbreviation: str) -> str:
        return f"{self.descriptor.official_portal_url}?query={abbreviation}"


class EigenportalConnector(StateLawConnector):
    """Einzeladapter für eigenständige Landesportale (BY, NW, SN, BB, HB, SL)."""

    def build_legal_deeplink(self, abbreviation: str) -> str:
        return f"{self.descriptor.official_portal_url}?search={abbreviation}"


def get_state_connector(land_code: str) -> StateLawConnector:
    code = land_code.upper()
    if code not in STATE_PORTAL_REGISTRY:
        raise KeyError(f"Unbekannter Bundesland-Code: {land_code}")
    desc = STATE_PORTAL_REGISTRY[code]
    if desc.portal_type == "verkuendungsblatt":
        return VerkuendungsblattConnector(desc)
    if desc.portal_type == "juris_bsxx":
        return BsXXJurisConnector(desc)
    return EigenportalConnector(desc)


class DNGOpenDataRequestGenerator:
    """Erzeugt rechtssichere Open-Data-Anträge nach dem Datennutzungsgesetz (DNG)."""

    @staticmethod
    def generate_dng_request(land_code: str, recipient_authority: str | None = None) -> str:
        desc = STATE_PORTAL_REGISTRY[land_code.upper()]
        authority = recipient_authority or f"Justizministerium / Staatskanzlei des Landes {desc.land_name}"
        today = date.today().strftime("%d.%m.%Y")
        return (
            f"Betreff: Antrag auf Bereitstellung amtlicher Rechtsnormen im offenen, maschinenlesbaren "
            f"Format (LegalDocML.de / XML) nach dem Datennutzungsgesetz (DNG) und § 5 UrhG\n"
            f"Datum: {today}\n"
            f"Empfänger: {authority}\n\n"
            f"Sehr geehrte Damen und Herren,\n\n"
            f"hiermit beantragen wir im Rahmen des gemeinnützigen Open-Source-Projekts LexAudit DE/EU "
            f"die Bereitstellung der im Landesrecht {desc.land_name} verkündeten Gesetze und "
            f"Rechtsverordnungen (Portal: {desc.gazette_url}) in einem strukturierten, offenen und "
            f"maschinenlesbaren Standardformat (vorzugsweise Akoma Ntoso / LegalDocML.de XML oder CSV/JSON "
            f"gemäß § 4 Abs. 1, § 7 DNG) unter ausdrücklicher Wahrung von § 5 Abs. 1 UrhG.\n\n"
            f"Hintergrund: Das bisherige Portal ({desc.official_portal_url}) ist als '{desc.machine_readable_status}' "
            f"eingestuft ({desc.notes}). Eine offene Schnittstelle vermeidet unnötige Doppelarbeit und stärkt "
            f"Transparenz sowie Rechtssicherheit.\n\n"
            f"Mit freundlichen Grüßen\n"
            f"LexAudit DE/EU Civic-Tech-Initiative"
        )
