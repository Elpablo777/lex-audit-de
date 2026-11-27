"""Deterministischer deutscher Rechts-Zitationsparser (QuantLaw- & GermanLegalGraph-Muster)."""

from __future__ import annotations

import re

from lexaudit_core.schemas import NormReference

NUM = r"\d{1,4}[a-z]?"
NUM_SEP = r"(?:\s*,\s*|\s+(?:und|oder|u\.|bzw\.)\s+|\s+bis(?:\s+und\s+mit)?\s+)"
NUMS = rf"{NUM}(?:{NUM_SEP}{NUM})*"

QUAL = (
    r"(?:Abs(?:atz)?)\.?\s*\d{1,2}(?:\s*(?:,|und|u\.|oder)\s*\d{1,2})*"
    r"|(?:Satz)\s*\d{1,2}"
    r"|(?:Nr\.|Nummer)\s*\d{1,3}[a-z]?"
    r"|(?:Alt\.?)\s*[1-9]"
    r"|(?:Buchst(?:abe|\.)?)\s*[a-z]"
    r"|(?:Halbsatz)\s*\d{1,2}"
)
QUALS = rf"(?:\s*,?\s*(?:{QUAL}))*"
IVM = r"\s+(?:i\.\s?V\.\s?m\.?|iVm|in\s+Verbindung\s+mit)"

LAW_ALIASES: dict[str, str] = {
    "GG": "de:bund:gg",
    "BGB": "de:bund:bgb",
    "EGBGB": "de:bund:egbgb",
    "EStG": "de:bund:estg",
    "ErbStG": "de:bund:erbstg",
    "SGB II": "de:bund:sgb2",
    "SGB X": "de:bund:sgb10",
    "SGB XII": "de:bund:sgb12",
    "WoGG": "de:bund:wogg",
    "BKGG": "de:bund:bkgg",
    "UVG": "de:bund:uvg",
    "VwGO": "de:bund:vwgo",
    "StVG": "de:bund:stvg",
    "UrhG": "de:bund:urhg",
    "RDG": "de:bund:rdg",
    "NJG": "de:land:ni:njg",
    "NBauO": "de:land:ni:nbauo",
    "NDüngGewNPVO": "de:land:ni:nduenggewnpvo",
    "NDüngGewNPVO,NI": "de:land:ni:nduenggewnpvo",
    "AEUV": "eu:treaty:aeuv",
    "EMRK": "intl:coe:emrk",
    "Bürgerlichen Gesetzbuchs": "de:bund:bgb",
    "Grundgesetzes": "de:bund:gg",
    "Bundes-Klimaschutzgesetzes": "de:bund:ksg",
}

_LAW_ALT = "|".join(re.escape(k) for k in sorted(LAW_ALIASES, key=len, reverse=True))

CITE_RE = re.compile(
    rf"(?P<sign>§§?|Art(?:ikel)?\.?)"
    rf"\s*"
    rf"(?P<nums>{NUMS})"
    rf"(?P<ff>\s*ff\.?)?"
    rf"(?P<quals>{QUALS})?"
    rf"(?P<ivm>{IVM})?"
    rf"(?P<law>\s+(?:des|der|dem|den)?\s*(?P<lawname>{_LAW_ALT})(?=\W|$))?",
    re.IGNORECASE,
)

EU_DIR_RE = re.compile(
    r"(?:Richtlinie|RL)\s+(?P<num>\d{2,4}/\d{1,4}/(?:EWG|EG|EU))",
    re.IGNORECASE,
)

CONDITION_CTX_RE = re.compile(
    r"(?:nach|gemäß|gem\.|entsprechend|aufgrund|auf\s+Grund|infolge|kraft|laut|"
    r"zufolge|anhand|im\s+Sinne|im\s+Rahmen|nach\s+Maßgabe|vorbehaltlich|"
    r"auf\s+Grundlage|unter\s+den\s+Voraussetzungen)\s*(?:des|der|dem|den|dieser|dieses)?\s*$",
    re.IGNORECASE,
)

TOKEN_RE = re.compile(
    rf"({NUM})|(bis(?:\s+und\s+mit)?)|(,)|((?:und|oder|u\.|bzw\.))",
    re.IGNORECASE,
)


def expand_nums(nums: str, max_range: int = 40) -> list[str]:
    """Expandiert '280, 241' -> ['280', '241'] oder '823 bis 826' -> ['823', ..., '826']."""
    out: list[str] = []
    last: str | None = None
    pending_range = False
    for m in TOKEN_RE.finditer(nums):
        num, bis, _comma, _conj = m.groups()
        if num:
            if pending_range and last and last.isdigit() and num.isdigit():
                lo, hi = int(last), int(num)
                if hi > lo and (hi - lo) <= max_range:
                    out.extend(str(n) for n in range(lo + 1, hi + 1))
                else:
                    out.append(num)
            else:
                out.append(num)
            last, pending_range = num, False
        elif bis:
            pending_range = True
        else:
            pending_range = False
    return out


def canonical_norm_id(law_prefix: str, sign: str, num: str) -> str:
    prefix = "art" if sign.lower().startswith("art") else "p"
    return f"{law_prefix}:{prefix}_{num.lower()}"


class QuantLawReferenceParser:
    """Deterministischer Querverweis- und Zitationsparser ohne KI-Tokens."""

    def extract_references(
        self,
        text: str,
        *,
        src_norm_id: str,
        default_law_prefix: str,
        known_norm_ids: set[str] | None = None,
        definition_norm_ids: set[str] | None = None,
    ) -> list[NormReference]:
        known = known_norm_ids or set()
        definitions = definition_norm_ids or set()
        refs: list[NormReference] = []
        seen: set[tuple[str, str, str]] = set()

        matches = list(CITE_RE.finditer(text))
        for idx, m in enumerate(matches):
            sign = "Art" if m.group("sign").lower().startswith("art") else "§"
            law_token = m.group("lawname")
            law_prefix = default_law_prefix
            if law_token:
                # Case-insensitive Lookup gegen LAW_ALIASES
                for k, v in LAW_ALIASES.items():
                    if k.lower() == law_token.lower():
                        law_prefix = v
                        break

            ctx = text[max(0, m.start() - 60) : m.start()]
            rel_type = "CONDITION_FOR" if CONDITION_CTX_RE.search(ctx) else "CITES"
            raw_citation = " ".join(m.group(0).split())
            evidence = " ".join(
                text[max(0, m.start() - 25) : min(len(text), m.end() + 25)].split()
            )

            for num in expand_nums(m.group("nums")):
                tgt = canonical_norm_id(law_prefix, sign, num)
                if tgt == src_norm_id:
                    continue
                actual_rel = "DEFINES" if tgt in definitions else rel_type
                resolved = tgt in known
                key = (src_norm_id, tgt, actual_rel)
                if key not in seen:
                    seen.add(key)
                    refs.append(
                        NormReference(
                            src_norm_id=src_norm_id,
                            tgt_norm_id=tgt,
                            relation_type=actual_rel,
                            evidence=evidence,
                            resolved=resolved,
                            raw_citation=raw_citation,
                        )
                    )

            # i.V.m.-Folgeglied zusätzlich verknüpfen
            if m.group("ivm") and idx + 1 < len(matches):
                nxt = matches[idx + 1]
                nxt_sign = "Art" if nxt.group("sign").lower().startswith("art") else "§"
                nxt_law_token = nxt.group("lawname")
                nxt_prefix = default_law_prefix
                if nxt_law_token:
                    for k, v in LAW_ALIASES.items():
                        if k.lower() == nxt_law_token.lower():
                            nxt_prefix = v
                            break
                for num in expand_nums(nxt.group("nums")):
                    tgt = canonical_norm_id(nxt_prefix, nxt_sign, num)
                    key = (src_norm_id, tgt, "CITES")
                    if tgt != src_norm_id and key not in seen:
                        seen.add(key)
                        refs.append(
                            NormReference(
                                src_norm_id=src_norm_id,
                                tgt_norm_id=tgt,
                                relation_type="CITES",
                                evidence=f"{evidence} [i.V.m.]",
                                resolved=tgt in known,
                                raw_citation=raw_citation,
                            )
                        )

        for eu_m in EU_DIR_RE.finditer(text):
            celex_hint = eu_m.group("num").lower().replace("/", "_")
            tgt = f"eu:dir:{celex_hint}"
            key = (src_norm_id, tgt, "TRANSPOSES")
            if key not in seen:
                seen.add(key)
                refs.append(
                    NormReference(
                        src_norm_id=src_norm_id,
                        tgt_norm_id=tgt,
                        relation_type="TRANSPOSES",
                        evidence=eu_m.group(0),
                        resolved=tgt in known,
                        raw_citation=eu_m.group(0),
                    )
                )

        return refs
