"""Deterministische XML- & Rechtsreferenz-Parser."""

from lexaudit_core.parsers.reference_parser import (
    LAW_ALIASES,
    QuantLawReferenceParser,
    canonical_norm_id,
    expand_nums,
)
from lexaudit_core.parsers.xml_parsers import (
    ParsedLegislationBundle,
    compute_text_hash,
    parse_formex_xml,
    parse_gii_xml,
    parse_legaldocml_xml,
    parse_rii_xml,
)

__all__ = [
    "LAW_ALIASES",
    "ParsedLegislationBundle",
    "QuantLawReferenceParser",
    "canonical_norm_id",
    "compute_text_hash",
    "expand_nums",
    "parse_formex_xml",
    "parse_gii_xml",
    "parse_legaldocml_xml",
    "parse_rii_xml",
]
