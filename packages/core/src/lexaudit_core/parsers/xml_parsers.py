"""Deterministische XML-Parser (0 KI-Tokens) für GII-XML, LegalDocML.de, RII-XML & Formex-XML."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from lxml import etree

from lexaudit_core.guardrails import PIISanitizer
from lexaudit_core.schemas import (
    ComponentTemporalVersion,
    CourtDecision,
    CourtLevel,
    HierarchyRank,
    JurisdictionLevel,
    LegalAct,
    NormType,
    NormUnit,
    TemporalStatus,
)


def compute_text_hash(text: str) -> str:
    """Erzeugt einen stabilen SHA-256-Hash für Änderungs-Diffs pro Einzelnorm."""
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_iso_date(raw: str | None, fallback: date | None = None) -> date:
    if not raw:
        return fallback or date(2026, 1, 1)
    cleaned = raw.strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return fallback or date(2026, 1, 1)


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


@dataclass(frozen=True)
class ParsedLegislationBundle:
    act: LegalAct
    norms: list[NormUnit]
    versions: list[ComponentTemporalVersion]
    transposition_deadline: date | None = None


def parse_gii_xml(
    xml_bytes: bytes,
    source_url: str = "https://www.gesetze-im-internet.de/gii-toc.xml",
    legal_domain: str = "Bundesrecht",
) -> ParsedLegislationBundle:
    """Parst amtliches Gesetze-im-Internet-XML deterministisch ohne LLM-Tokens."""
    root = etree.fromstring(xml_bytes)
    norm_elems = root.findall(".//norm")
    if not norm_elems:
        raise ValueError("GII-XML enthält keine <norm>-Elemente.")

    first_meta = norm_elems[0].find("metadaten")
    jurabk = (
        first_meta.findtext("jurabk")
        if first_meta is not None and first_meta.findtext("jurabk")
        else "BUND"
    )
    doknr = root.get("doknr") or _slug(jurabk)
    ausfertigung = _parse_iso_date(
        first_meta.findtext("ausfertigung-datum") if first_meta is not None else None
    )
    act_id = f"de:bund:{_slug(jurabk)}"
    eli_uri = f"eli/bund/{_slug(jurabk)}/{doknr}"
    hierarchy = (
        HierarchyRank.GRUNDGESETZ if jurabk.upper() == "GG" else HierarchyRank.BUNDESRECHT
    )
    norm_type = (
        NormType.CONSTITUTION if jurabk.upper() == "GG" else NormType.FORMAL_STATUTE
    )
    act = LegalAct(
        act_id=act_id,
        eli_uri=eli_uri,
        title=jurabk,
        short_title=jurabk,
        jurisdiction_level=JurisdictionLevel.BUND,
        norm_type=norm_type,
        hierarchy_rank=int(hierarchy),
        promulgation_date=ausfertigung,
        source_url=source_url,
        license="§ 5 UrhG gemeinfrei",
    )

    norms: list[NormUnit] = []
    versions: list[ComponentTemporalVersion] = []
    for elem in norm_elems:
        meta = elem.find("metadaten")
        enbez = meta.findtext("enbez") if meta is not None else None
        if not enbez:
            continue
        heading = (meta.findtext("titel") or "") if meta is not None else ""
        paragraphs = [
            " ".join("".join(p.itertext()).split())
            for p in elem.findall(".//textdaten//P")
        ]
        full_text = "\n".join(p for p in paragraphs if p)
        if not full_text:
            full_text = " ".join("".join(elem.itertext()).split())

        norm_id = f"{act_id}:{_slug(enbez)}"
        norms.append(
            NormUnit(
                norm_id=norm_id,
                act_id=act_id,
                eli_uri=f"{eli_uri}/{_slug(enbez)}",
                designation=enbez.strip(),
                heading=heading.strip(),
                hierarchy_rank=int(hierarchy),
                legal_domain=legal_domain,
                status=TemporalStatus.IN_FORCE,
            )
        )
        t_hash = compute_text_hash(full_text)
        versions.append(
            ComponentTemporalVersion(
                version_id=f"{norm_id}@{ausfertigung.isoformat()}:{t_hash[:8]}",
                norm_id=norm_id,
                valid_from=ausfertigung,
                valid_to=None,
                promulgation_date=ausfertigung,
                status=TemporalStatus.IN_FORCE,
                text_hash=t_hash,
                full_text=full_text,
                context_header=f"[{jurabk} | {enbez.strip()} | {heading.strip()}]",
            )
        )

    return ParsedLegislationBundle(act=act, norms=norms, versions=versions)


def parse_legaldocml_xml(
    xml_bytes: bytes,
    source_url: str = "https://testphase.rechtsinformationen.bund.de/v1/legislation",
    legal_domain: str = "Sozialrecht",
) -> ParsedLegislationBundle:
    """Parst Akoma Ntoso / LegalDocML.de XML (NeuRIS-Standardformat)."""
    root = etree.fromstring(xml_bytes)
    ns = {"akn": root.nsmap.get(None, "")} if root.nsmap.get(None) else {}

    def _find(node: etree._Element, path: str) -> etree._Element | None:
        if ns:
            prefixed = "/".join(
                f"akn:{seg}" if seg and not seg.startswith(".") and ":" not in seg else seg
                for seg in path.split("/")
            )
            return node.find(prefixed, namespaces=ns)
        return node.find(path)

    def _findall(node: etree._Element, path: str) -> list[etree._Element]:
        if ns:
            prefixed = "/".join(
                f"akn:{seg}" if seg and not seg.startswith(".") and ":" not in seg else seg
                for seg in path.split("/")
            )
            return list(node.findall(prefixed, namespaces=ns))
        return list(node.findall(path))

    act_el = _find(root, ".//act")
    if act_el is None:
        raise ValueError("LegalDocML.de-Dokument enthält kein <act>-Element.")

    frbr_work_uri = _find(act_el, ".//FRBRWork/FRBRuri")
    frbr_name = _find(act_el, ".//FRBRWork/FRBRname")
    frbr_date = _find(act_el, ".//FRBRExpression/FRBRdate")
    if frbr_date is None:
        frbr_date = _find(act_el, ".//FRBRWork/FRBRdate")
    eli_uri = frbr_work_uri.get("value") if frbr_work_uri is not None else act_el.get("name", "act")
    title = (
        frbr_name.get("value")
        if frbr_name is not None and frbr_name.get("value")
        else (act_el.get("name") or "Unbenannter Rechtsakt")
    )
    valid_from = _parse_iso_date(frbr_date.get("date") if frbr_date is not None else None)
    act_slug = _slug(act_el.get("name") or title)
    act_id = f"de:bund:{act_slug}"

    act = LegalAct(
        act_id=act_id,
        eli_uri=eli_uri,
        title=title,
        short_title=act_el.get("name") or title,
        jurisdiction_level=JurisdictionLevel.BUND,
        norm_type=NormType.FORMAL_STATUTE,
        hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
        promulgation_date=valid_from,
        source_url=source_url,
        license="§ 5 UrhG gemeinfrei",
    )

    norms: list[NormUnit] = []
    versions: list[ComponentTemporalVersion] = []
    for art in _findall(act_el, ".//body//article"):
        num_el = _find(art, "num")
        heading_el = _find(art, "heading")
        designation = (num_el.text or art.get("eId") or "§").strip() if num_el is not None else "§"
        heading = (heading_el.text or "").strip() if heading_el is not None else ""
        paras = [
            " ".join("".join(p.itertext()).split())
            for p in _findall(art, ".//paragraph")
        ]
        full_text = "\n".join(p for p in paras if p)
        if not full_text:
            full_text = " ".join("".join(art.itertext()).split())

        norm_id = f"{act_id}:{_slug(designation)}"
        norms.append(
            NormUnit(
                norm_id=norm_id,
                act_id=act_id,
                eli_uri=f"{eli_uri}/{art.get('eId', _slug(designation))}",
                designation=designation,
                heading=heading,
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain=legal_domain,
                status=TemporalStatus.IN_FORCE,
            )
        )
        t_hash = compute_text_hash(full_text)
        versions.append(
            ComponentTemporalVersion(
                version_id=f"{norm_id}@{valid_from.isoformat()}:{t_hash[:8]}",
                norm_id=norm_id,
                valid_from=valid_from,
                valid_to=None,
                promulgation_date=valid_from,
                status=TemporalStatus.IN_FORCE,
                text_hash=t_hash,
                full_text=full_text,
                context_header=f"[{title} | {designation} | {heading} | Stand {valid_from.isoformat()}]",
            )
        )
    return ParsedLegislationBundle(act=act, norms=norms, versions=versions)


def parse_rii_xml(
    xml_bytes: bytes,
    source_url: str = "https://www.rechtsprechung-im-internet.de/rii-toc.xml",
) -> CourtDecision:
    """Parst amtliches Rechtsprechung-im-Internet-XML inkl. automatischem PII-Filter."""
    root = etree.fromstring(xml_bytes)
    doknr = (root.findtext("doknr") or "RII_UNKNOWN").strip()
    gericht = (root.findtext("gericht") or "BGH").strip()
    spruchkoerper = (root.findtext("spruchkoerper") or "").strip()
    entsch_date = _parse_iso_date(root.findtext("entsch-datum"))
    az = (root.findtext("aktenzeichen") or "o. Az.").strip()
    ecli = (root.findtext("ecli") or f"ECLI:DE:{_slug(gericht).upper()}:{entsch_date.year}:{doknr}").strip()

    def _collect_text(tag: str) -> str:
        el = root.find(tag)
        if el is None:
            return ""
        return PIISanitizer.sanitize(" ".join("".join(el.itertext()).split()))

    leitsatz = _collect_text("leitsatz")
    tenor = _collect_text("tenor")
    gruende = _collect_text("gruende") or _collect_text("content")
    full_text = "\n\n".join(part for part in [leitsatz, tenor, gruende] if part)

    level_upper = gericht.upper()
    if "BVERFG" in level_upper:
        court_level = CourtLevel.BVERFG
    elif level_upper in {"BGH", "BVERWG", "BFH", "BSG", "BAG", "BPATG"}:
        court_level = CourtLevel.OBERSTES_BUNDESGERICHT
    elif "OVG" in level_upper or "VGH" in level_upper or "OLG" in level_upper:
        court_level = CourtLevel.OVG_OBERLANDESGERICHT
    else:
        court_level = CourtLevel.FACHGERICHT

    court_display = f"{gericht} ({spruchkoerper})".strip() if spruchkoerper else gericht
    return CourtDecision(
        decision_id=f"case:{_slug(ecli)}",
        ecli=ecli,
        court_level=court_level,
        court_name=court_display,
        decision_date=entsch_date,
        file_number=az,
        leitsatz=leitsatz,
        tenor=tenor,
        full_text=full_text or leitsatz or az,
        source_url=source_url,
        license="§ 5 UrhG gemeinfrei",
    )


def parse_formex_xml(
    xml_bytes: bytes,
    source_url: str = "https://eur-lex.europa.eu/",
    legal_domain: str = "EU-Umweltrecht",
) -> ParsedLegislationBundle:
    """Parst EUR-Lex Formex-XML inkl. Umsetzungsfrist (`DATE.TRANSPOSITION`)."""
    root = etree.fromstring(xml_bytes)
    doc_ref = root.find(".//DOCUMENT.REF")
    celex = (doc_ref.findtext("CELEX") if doc_ref is not None else None) or "CELEX_UNKNOWN"
    eli = (doc_ref.findtext("ELI") if doc_ref is not None else None) or f"http://data.europa.eu/eli/{_slug(celex)}"
    doc_date = _parse_iso_date(doc_ref.findtext("DATE.DOCUMENT") if doc_ref is not None else None)
    trans_raw = doc_ref.findtext("DATE.TRANSPOSITION") if doc_ref is not None else None
    transposition_deadline = _parse_iso_date(trans_raw) if trans_raw else None

    title_el = root.find(".//TITLE")
    title = " ".join("".join(title_el.itertext()).split()) if title_el is not None else celex
    is_directive = "L" in celex or "richtlinie" in title.lower()
    act_id = f"eu:celex:{_slug(celex)}"

    act = LegalAct(
        act_id=act_id,
        eli_uri=eli,
        title=title,
        short_title=celex,
        jurisdiction_level=JurisdictionLevel.EU,
        norm_type=NormType.EU_DIRECTIVE if is_directive else NormType.EU_REGULATION,
        hierarchy_rank=int(HierarchyRank.EU_RECHT),
        promulgation_date=doc_date,
        source_url=source_url,
        license="Beschluss 2011/833/EU",
    )

    norms: list[NormUnit] = []
    versions: list[ComponentTemporalVersion] = []
    for art in root.findall(".//ARTICLE"):
        art_ident = art.get("IDENTIFIER") or "001"
        ti_art = (art.findtext("TI.ART") or f"Artikel {art_ident.lstrip('0') or '1'}").strip()
        alineas = [
            " ".join("".join(al.itertext()).split())
            for al in art.findall(".//ALINEA")
        ]
        full_text = "\n".join(a for a in alineas if a) or " ".join("".join(art.itertext()).split())
        norm_id = f"{act_id}:{_slug(ti_art)}"
        norms.append(
            NormUnit(
                norm_id=norm_id,
                act_id=act_id,
                eli_uri=f"{eli}/art_{art_ident}",
                designation=ti_art,
                heading=title[:120],
                hierarchy_rank=int(HierarchyRank.EU_RECHT),
                legal_domain=legal_domain,
                status=TemporalStatus.IN_FORCE,
            )
        )
        t_hash = compute_text_hash(full_text)
        versions.append(
            ComponentTemporalVersion(
                version_id=f"{norm_id}@{doc_date.isoformat()}:{t_hash[:8]}",
                norm_id=norm_id,
                valid_from=doc_date,
                valid_to=None,
                promulgation_date=doc_date,
                status=TemporalStatus.IN_FORCE,
                text_hash=t_hash,
                full_text=full_text,
                context_header=f"[{celex} | {ti_art} | EU-Anwendungsvorrang]",
            )
        )

    return ParsedLegislationBundle(
        act=act,
        norms=norms,
        versions=versions,
        transposition_deadline=transposition_deadline,
    )
