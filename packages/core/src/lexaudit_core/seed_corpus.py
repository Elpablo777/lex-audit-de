"""Kuratierter Pilot-Korpus (Bund + Niedersachsen + EU + BVerfG/BVerwG/OVG + DIP) für deterministische Analysen & Tests."""

from __future__ import annotations

from datetime import date

from lexaudit_core.embeddings import EmbeddingAdapter, chunk_court_decision, chunk_temporal_version
from lexaudit_core.parsers.xml_parsers import compute_text_hash
from lexaudit_core.schemas import (
    ComponentTemporalVersion,
    CourtDecision,
    CourtLevel,
    HierarchyRank,
    JurisdictionLevel,
    LegalAct,
    NormType,
    NormUnit,
    ParliamentaryDoc,
    TemporalStatus,
)
from lexaudit_core.storage import SQLiteStorageBackend


def _make_version(
    norm_id: str,
    header: str,
    text: str,
    valid_from: date,
    valid_to: date | None = None,
    status: TemporalStatus = TemporalStatus.IN_FORCE,
    supersedes: str | None = None,
) -> ComponentTemporalVersion:
    h = compute_text_hash(text)
    return ComponentTemporalVersion(
        version_id=f"{norm_id}@{valid_from.isoformat()}:{h[:8]}",
        norm_id=norm_id,
        valid_from=valid_from,
        valid_to=valid_to,
        promulgation_date=valid_from,
        status=status,
        text_hash=h,
        full_text=text,
        context_header=header,
        supersedes_version_id=supersedes,
    )


def load_pilot_corpus(storage: SQLiteStorageBackend) -> dict[str, int]:
    """Lädt den vollständigen 2026er Pilot-Korpus (Bund + Niedersachsen + EU + Rechtsprechung) deterministisch."""
    embedder = EmbeddingAdapter(storage.settings)

    acts = [
        LegalAct(
            act_id="intl:coe:emrk",
            eli_uri="eli/coe/ets/005",
            title="Konvention zum Schutze der Menschenrechte und Grundfreiheiten (EMRK)",
            short_title="EMRK",
            jurisdiction_level=JurisdictionLevel.INTERNATIONAL,
            norm_type=NormType.TREATY,
            hierarchy_rank=int(HierarchyRank.VOELKERRECHT_ALLG),
            promulgation_date=date(1952, 12, 5),
            source_url="https://hudoc.echr.coe.int/",
        ),
        LegalAct(
            act_id="eu:dir:91_676_ewg",
            eli_uri="http://data.europa.eu/eli/dir/1991/676/oj",
            title="Richtlinie 91/676/EWG zum Schutz der Gewässer vor Verunreinigung durch Nitrat (Nitratrichtlinie)",
            short_title="RL 91/676/EWG",
            jurisdiction_level=JurisdictionLevel.EU,
            norm_type=NormType.EU_DIRECTIVE,
            hierarchy_rank=int(HierarchyRank.EU_RECHT),
            promulgation_date=date(1991, 12, 12),
            source_url="https://eur-lex.europa.eu/eli/dir/1991/676/oj",
            license="Beschluss 2011/833/EU",
        ),
        LegalAct(
            act_id="eu:treaty:aeuv",
            eli_uri="http://data.europa.eu/eli/treaty/tfeu_2012/oj",
            title="Vertrag über die Arbeitsweise der Europäischen Union (AEUV)",
            short_title="AEUV",
            jurisdiction_level=JurisdictionLevel.EU,
            norm_type=NormType.EU_REGULATION,
            hierarchy_rank=int(HierarchyRank.EU_RECHT),
            promulgation_date=date(2012, 10, 26),
            source_url="https://eur-lex.europa.eu/eli/treaty/tfeu_2012/oj",
            license="Beschluss 2011/833/EU",
        ),
        LegalAct(
            act_id="de:bund:gg",
            eli_uri="eli/bund/bgbl-1/1949/s1",
            title="Grundgesetz für die Bundesrepublik Deutschland",
            short_title="GG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.CONSTITUTION,
            hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
            promulgation_date=date(1949, 5, 23),
            source_url="https://www.gesetze-im-internet.de/gg/",
        ),
        LegalAct(
            act_id="de:bund:erbstg",
            eli_uri="eli/bund/bgbl-1/1997/s378",
            title="Erbschaftsteuer- und Schenkungsteuergesetz (ErbStG)",
            short_title="ErbStG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(1997, 2, 27),
            source_url="https://www.gesetze-im-internet.de/erbstg_1974/",
        ),
        LegalAct(
            act_id="de:bund:sgb2",
            eli_uri="eli/bund/bgbl-1/2003/s2954",
            title="Sozialgesetzbuch Zweites Buch – Bürgergeld, Grundsicherung für Arbeitsuchende (SGB II)",
            short_title="SGB II",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(2003, 12, 24),
            source_url="https://www.gesetze-im-internet.de/sgb_2/",
        ),
        LegalAct(
            act_id="de:bund:wogg",
            eli_uri="eli/bund/bgbl-1/2008/s1856",
            title="Wohngeldgesetz (WoGG)",
            short_title="WoGG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(2008, 9, 24),
            source_url="https://www.gesetze-im-internet.de/wogg/",
        ),
        LegalAct(
            act_id="de:bund:bkgg",
            eli_uri="eli/bund/bgbl-1/1995/s1378",
            title="Bundeskindergeldgesetz (BKGG)",
            short_title="BKGG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(1995, 10, 11),
            source_url="https://www.gesetze-im-internet.de/bkgg_1996/",
        ),
        LegalAct(
            act_id="de:bund:estg",
            eli_uri="eli/bund/bgbl-1/2009/s3366",
            title="Einkommensteuergesetz (EStG)",
            short_title="EStG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(2009, 10, 8),
            source_url="https://www.gesetze-im-internet.de/estg/",
        ),
        LegalAct(
            act_id="de:bund:vwgo",
            eli_uri="eli/bund/bgbl-1/1960/s17",
            title="Verwaltungsgerichtsordnung (VwGO)",
            short_title="VwGO",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(1960, 1, 21),
            source_url="https://www.gesetze-im-internet.de/vwgo/",
        ),
        LegalAct(
            act_id="de:bund:bgb",
            eli_uri="eli/bund/bgbl-1/1896/s195",
            title="Bürgerliches Gesetzbuch (BGB)",
            short_title="BGB",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(1896, 8, 18),
            source_url="https://www.gesetze-im-internet.de/bgb/",
        ),
        LegalAct(
            act_id="de:bund:stvg",
            eli_uri="eli/bund/bgbl-1/2003/s310",
            title="Straßenverkehrsgesetz (StVG)",
            short_title="StVG",
            jurisdiction_level=JurisdictionLevel.BUND,
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
            promulgation_date=date(2003, 3, 5),
            source_url="https://www.gesetze-im-internet.de/stvg/",
        ),
        LegalAct(
            act_id="de:land:ni:njg",
            eli_uri="eli/land/ni/ndsgvbl/2014/s436",
            title="Niedersächsisches Justizgesetz (NJG)",
            short_title="NJG",
            jurisdiction_level=JurisdictionLevel.LAND,
            land_code="NI",
            norm_type=NormType.FORMAL_STATUTE,
            hierarchy_rank=int(HierarchyRank.LANDESRECHT),
            promulgation_date=date(2014, 12, 16),
            source_url="https://www.verkuendung-niedersachsen.de/",
        ),
        LegalAct(
            act_id="de:land:ni:nduenggewnpvo",
            eli_uri="eli/land/ni/ndsgvbl/2026/106",
            title="Niedersächsische Verordnung über düngerechtliche Anforderungen zum Gewässerschutz (NDüngGewNPVO,NI)",
            short_title="NDüngGewNPVO,NI",
            jurisdiction_level=JurisdictionLevel.LAND,
            land_code="NI",
            norm_type=NormType.ORDINANCE,
            hierarchy_rank=int(HierarchyRank.KOMMUNAL_UND_VV),
            promulgation_date=date(2026, 5, 15),
            source_url="https://www.verkuendung-niedersachsen.de/ndsgvbl/2026/106/",
        ),
        LegalAct(
            act_id="de:land:ni:klimavv",
            eli_uri="eli/land/ni/ndsmbl/2020/s210",
            title="Niedersächsische Verwaltungsvorschrift Klimaschutz-Vollzugsleitlinie (abgelaufene Befristung)",
            short_title="Nds. Klima-VV",
            jurisdiction_level=JurisdictionLevel.LAND,
            land_code="NI",
            norm_type=NormType.ADMIN_DIRECTIVE,
            hierarchy_rank=int(HierarchyRank.KOMMUNAL_UND_VV),
            promulgation_date=date(2020, 6, 1),
            source_url="https://www.verkuendung-niedersachsen.de/",
        ),
    ]
    for act in acts:
        storage.upsert_act(act)

    norm_specs: list[tuple[NormUnit, list[ComponentTemporalVersion]]] = [
        (
            NormUnit(
                norm_id="de:bund:gg:art_1",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_1",
                designation="Art. 1",
                heading="Menschenwürde, Grundrechtsbindung",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Verfassungsrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_1",
                    "[GG | Art. 1 | Menschenwürde]",
                    "(1) Die Würde des Menschen ist unantastbar. Sie zu achten und zu schützen ist Verpflichtung aller staatlichen Gewalt. In Verbindung mit Art. 20 Abs. 1 GG gewährleistet dies das menschenwürdige Existenzminimum.",
                    date(1949, 5, 24),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:gg:art_3",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_3",
                designation="Art. 3",
                heading="Gleichheit vor dem Gesetz",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Verfassungsrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_3",
                    "[GG | Art. 3 | Gleichheitsgebot]",
                    "(1) Alle Menschen sind vor dem Gesetz gleich. Im Steuerrecht verlangt Art. 3 Abs. 1 GG Belastungsgleichheit und Folgerichtigkeit bei Verschonungsregelungen.",
                    date(1949, 5, 24),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:gg:art_20",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_20",
                designation="Art. 20",
                heading="Bundesstaatliche Verfassung; Sozialstaat",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Verfassungsrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_20",
                    "[GG | Art. 20 | Sozialstaatsprinzip]",
                    "(1) Die Bundesrepublik Deutschland ist ein demokratischer und sozialer Bundesstaat. Im Zusammenwirken mit Art. 1 Abs. 1 GG sichert das Sozialstaatsgebot das Existenzminimum.",
                    date(1949, 5, 24),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:gg:art_20a",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_20a",
                designation="Art. 20a",
                heading="Schutz der natürlichen Lebensgrundlagen",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Umweltrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_20a",
                    "[GG | Art. 20a | Klimaschutz und intertemporale Freiheit]",
                    "Der Staat schützt auch in Verantwortung für die künftigen Generationen die natürlichen Lebensgrundlagen und die Tiere im Rahmen der verfassungsmäßigen Ordnung durch die Gesetzgebung.",
                    date(2002, 8, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:gg:art_31",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_31",
                designation="Art. 31",
                heading="Vorrang des Bundesrechts",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Verfassungsrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_31",
                    "[GG | Art. 31 | Bundesrecht bricht Landesrecht]",
                    "Bundesrecht bricht Landesrecht.",
                    date(1949, 5, 24),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:gg:art_100",
                act_id="de:bund:gg",
                eli_uri="eli/bund/bgbl-1/1949/s1/art_100",
                designation="Art. 100",
                heading="Konkrete Normenkontrolle",
                hierarchy_rank=int(HierarchyRank.GRUNDGESETZ),
                legal_domain="Verfassungsrecht",
            ),
            [
                _make_version(
                    "de:bund:gg:art_100",
                    "[GG | Art. 100 | Vorlagepflicht der Fachgerichte]",
                    "(1) Hält ein Gericht ein Gesetz, auf dessen Gültigkeit es bei der Entscheidung ankommt, für verfassungswidrig, so ist das Verfahren auszusetzen und die Entscheidung des Bundesverfassungsgerichts einzuholen.",
                    date(1949, 5, 24),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:erbstg:p_13a",
                act_id="de:bund:erbstg",
                eli_uri="eli/bund/bgbl-1/1997/s378/p_13a",
                designation="§ 13a",
                heading="Steuerbefreiung für Betriebsvermögen",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Steuerrecht",
            ),
            [
                _make_version(
                    "de:bund:erbstg:p_13a",
                    "[ErbStG | § 13a | Fassung 2016–2025]",
                    "(1) Begünstigtes Vermögen im Sinne des § 13b Absatz 2 bleibt zu 85 Prozent steuerfrei, wenn der Wert 26 Millionen Euro nicht übersteigt (historische Übergangsfassung).",
                    date(2016, 7, 1),
                    valid_to=date(2026, 1, 1),
                    status=TemporalStatus.REPEALED,
                ),
                _make_version(
                    "de:bund:erbstg:p_13a",
                    "[ErbStG | § 13a | Steuerbefreiung für Betriebsvermögen]",
                    "(1) Begünstigtes Vermögen im Sinne des § 13b Absatz 2 bleibt vorbehaltlich des Satzes 2 zu 85 Prozent steuerfrei (Verschonungsabschlag), wenn der Wert des begünstigten Vermögens insgesamt 26 Millionen Euro nicht übersteigt. Überschreitet der Wert die Prüfschwelle von 26 Millionen Euro, erfolgt bei Großerwerben eine Abschmelzung nach § 13c oder eine Verschonungsbedarfsprüfung nach § 28a ErbStG.",
                    date(2026, 1, 1),
                ),
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:erbstg:p_28a",
                act_id="de:bund:erbstg",
                eli_uri="eli/bund/bgbl-1/1997/s378/p_28a",
                designation="§ 28a",
                heading="Verschonungsbedarfsprüfung",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Steuerrecht",
            ),
            [
                _make_version(
                    "de:bund:erbstg:p_28a",
                    "[ErbStG | § 28a | Verschonungsbedarfsprüfung]",
                    "(1) Überschreitet der Erwerb begünstigten Vermögens die Grenze von 26 Millionen Euro nach § 13a ErbStG, ist die auf das begünstigte Vermögen entfallende Steuer auf Antrag ganz oder teilweise zu erlassen, soweit der Erwerber nachweist, dass er persönlich nicht in der Lage ist, die Steuer aus verfügbarem Privatvermögen (50 Prozent) zu begleichen.",
                    date(2016, 7, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:sgb2:p_11b",
                act_id="de:bund:sgb2",
                eli_uri="eli/bund/bgbl-1/2003/s2954/p_11b",
                designation="§ 11b",
                heading="Absetzbeträge vom Einkommen",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Sozialrecht",
            ),
            [
                _make_version(
                    "de:bund:sgb2:p_11b",
                    "[SGB II | § 11b | Fassung 2023–2025]",
                    "(3) Bei erwerbsfähigen Leistungsberechtigten bleiben zwischen 100 Euro und 520 Euro 20 Prozent und zwischen 520 Euro und 1000 Euro 30 Prozent anrechnungsfrei.",
                    date(2023, 7, 1),
                    valid_to=date(2026, 1, 1),
                    status=TemporalStatus.REPEALED,
                ),
                _make_version(
                    "de:bund:sgb2:p_11b",
                    "[SGB II | § 11b | Absetzbeträge vom Einkommen]",
                    "(1) Vom Einkommen sind Steuern, Sozialversicherungsbeiträge und Erwerbstätigenfreibeträge abzusetzen. (3) Zwischen 100 Euro und 520 Euro sind 20 Prozent, zwischen 520 Euro und 1.000 Euro 30 Prozent und bis 1.200 Euro (mit Kind 1.500 Euro) 10 Prozent anrechnungsfrei. Darüber hinaus greift eine Anrechnung von 100 Prozent, was im Zusammenspiel mit § 19 WoGG und § 6a BKGG zu Grenzbelastungen über 100 Prozent führen kann.",
                    date(2026, 1, 1),
                ),
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:wogg:p_19",
                act_id="de:bund:wogg",
                eli_uri="eli/bund/bgbl-1/2008/s1856/p_19",
                designation="§ 19",
                heading="Höhe des Wohngeldes und Einkommensanrechnung",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Sozialrecht",
            ),
            [
                _make_version(
                    "de:bund:wogg:p_19",
                    "[WoGG | § 19 | Wohngeldberechnung]",
                    "(1) Das ungerundete monatliche Wohngeld mindert sich mit steigendem Gesamteinkommen nach § 14 WoGG. Bei gleichzeitigem Bezug von Kinderzuschlag nach § 6a BKGG und Lohnsteuerabzug nach § 32a EStG entstehen kumulative Entzugseffekte; die geplante Wohngeldreform 2026 sieht jährliche Kürzungen ab 2028 vor.",
                    date(2025, 1, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:bkgg:p_6a",
                act_id="de:bund:bkgg",
                eli_uri="eli/bund/bgbl-1/1995/s1378/p_6a",
                designation="§ 6a",
                heading="Kinderzuschlag und Einkommensanrechnung",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Sozialrecht",
            ),
            [
                _make_version(
                    "de:bund:bkgg:p_6a",
                    "[BKGG | § 6a | Kinderzuschlag]",
                    "(1) Personen erhalten für unverheiratete Kinder unter 25 Jahren Kinderzuschlag, wenn durch das eigene Einkommen zusammen mit Wohngeld nach § 19 WoGG und Kinderzuschlag Hilfebedürftigkeit nach § 9 SGB II vermieden wird. (6) Eigenes Erwerbseinkommen der Eltern wird zu 45 Prozent auf den Kinderzuschlag angerechnet; beim Wegfall von Wohngeld droht der Verlust gekoppelter Ansprüche auf Bildung und Teilhabe.",
                    date(2025, 1, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:estg:p_32a",
                act_id="de:bund:estg",
                eli_uri="eli/bund/bgbl-1/2009/s3366/p_32a",
                designation="§ 32a",
                heading="Einkommensteuertarif",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Steuerrecht",
            ),
            [
                _make_version(
                    "de:bund:estg:p_32a",
                    "[EStG | § 32a | Einkommensteuertarif]",
                    "(1) Die tarifliche Einkommensteuer bemisst sich nach dem zu versteuernden Einkommen oberhalb des Grundfreibetrags und steigt in der Progressionszone ab 14 Prozent linear an. Gemeinsam mit Sozialabgaben sowie Anrechnungen nach § 11b SGB II, § 19 WoGG und § 6a BKGG wirkt sie als Grenzbelastung auf jeden hinzuverdienten Euro.",
                    date(2026, 1, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:vwgo:p_47",
                act_id="de:bund:vwgo",
                eli_uri="eli/bund/bgbl-1/1960/s17/p_47",
                designation="§ 47",
                heading="Normenkontrolle durch Oberverwaltungsgerichte",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Verwaltungsprozessrecht",
            ),
            [
                _make_version(
                    "de:bund:vwgo:p_47",
                    "[VwGO | § 47 | Prinzipale Normenkontrolle]",
                    "(1) Das Oberverwaltungsgericht entscheidet im Rahmen seiner Gerichtsbarkeit auf Antrag über die Gültigkeit von Satzungen und anderen im Rang unter dem Landesgesetz stehenden Rechtsvorschriften, sofern das Landesrecht dies bestimmt (in Niedersachsen § 75 NJG). (2) Der Antrag kann nur innerhalb eines Jahres nach Bekanntmachung der Rechtsvorschrift gestellt werden; bei Erfolg ist die Norm allgemeinverbindlich unwirksam.",
                    date(1960, 4, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:land:ni:njg:p_75",
                act_id="de:land:ni:njg",
                eli_uri="eli/land/ni/ndsgvbl/2014/s436/p_75",
                designation="§ 75",
                heading="Normenkontrolle untergesetzlichen Landesrechts",
                hierarchy_rank=int(HierarchyRank.LANDESRECHT),
                legal_domain="Verwaltungsprozessrecht",
            ),
            [
                _make_version(
                    "de:land:ni:njg:p_75",
                    "[NJG | § 75 | Nds. Normenkontrolle beim OVG Lüneburg]",
                    "Das Niedersächsische Oberverwaltungsgericht (OVG Lüneburg) entscheidet nach § 47 Abs. 1 Nr. 2 VwGO auch über die Gültigkeit von anderen im Rang unter dem Landesgesetz stehenden Rechtsvorschriften. Eine individuelle Bürger-Verfassungsbeschwerde zum Niedersächsischen Staatsgerichtshof besteht nicht.",
                    date(2015, 1, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:land:ni:nduenggewnpvo:p_2",
                act_id="de:land:ni:nduenggewnpvo",
                eli_uri="eli/land/ni/ndsgvbl/2026/106/p_2",
                designation="§ 2",
                heading="Ausweisung mit Nitrat belasteter Gebiete und Schutzmaßnahmen",
                hierarchy_rank=int(HierarchyRank.KOMMUNAL_UND_VV),
                legal_domain="Umweltrecht",
            ),
            [
                _make_version(
                    "de:land:ni:nduenggewnpvo:p_2",
                    "[NDüngGewNPVO,NI | § 2 | Nitrat-Gebietskulisse Niedersachsen]",
                    "(1) Zur Umsetzung der Richtlinie 91/676/EWG legt diese Landesverordnung abweichende Düngeregeln in den nitratbelasteten Gebieten Niedersachsens fest. (2) Soweit abweichende Ausnahmen für Grünlandflächen hinter den zwingenden Reduktionsvorgaben von Art. 5 RL 91/676/EWG und Art. 20a GG zurückbleiben, greift der EU-Anwendungsvorrang; binnen 1 Jahres ab Bekanntmachung (15.05.2026) ist die Normenkontrolle nach § 47 VwGO i.V.m. § 75 NJG beim OVG Lüneburg statthaft.",
                    date(2026, 5, 15),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="eu:dir:91_676_ewg:art_5",
                act_id="eu:dir:91_676_ewg",
                eli_uri="http://data.europa.eu/eli/dir/1991/676/oj/art_5",
                designation="Artikel 5",
                heading="Aktionsprogramme zum Schutz vor Nitratverunreinigung",
                hierarchy_rank=int(HierarchyRank.EU_RECHT),
                legal_domain="EU-Umweltrecht",
            ),
            [
                _make_version(
                    "eu:dir:91_676_ewg:art_5",
                    "[RL 91/676/EWG | Art. 5 | Aktionsprogramme (Frist 1993-12-20)]",
                    "(1) Die Mitgliedstaaten legen verpflichtende Aktionsprogramme fest, um die Verunreinigung durch Nitrat wirksam zu verringern; Umsetzungsfrist war der 20.12.1993.",
                    date(1991, 12, 12),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:land:ni:klimavv:p_4",
                act_id="de:land:ni:klimavv",
                eli_uri="eli/land/ni/ndsmbl/2020/s210/p_4",
                designation="§ 4",
                heading="Befristung und Verweis auf aufgehobene Norm",
                hierarchy_rank=int(HierarchyRank.KOMMUNAL_UND_VV),
                legal_domain="Umweltrecht",
                status=TemporalStatus.EXPIRED,
            ),
            [
                _make_version(
                    "de:land:ni:klimavv:p_4",
                    "[Nds. Klima-VV | § 4 | Abgelaufene Befristung & Verweis]",
                    "(1) Diese Verwaltungsvorschrift tritt nach Ablauf von fünf Jahren am 31.05.2025 außer Kraft. Für Zuständigkeiten gilt § 999 des aufgehobenen NdsVwAltG entsprechend.",
                    date(2020, 6, 1),
                    valid_to=date(2025, 5, 31),
                    status=TemporalStatus.EXPIRED,
                )
            ],
        ),
        # Schein-Konflikt-Kontrollnormen (lex specialis — KEIN Rechtsfehler!)
        (
            NormUnit(
                norm_id="de:bund:bgb:p_823",
                act_id="de:bund:bgb",
                eli_uri="eli/bund/bgbl-1/1896/s195/p_823",
                designation="§ 823",
                heading="Schadensersatzpflicht",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Zivilrecht",
            ),
            [
                _make_version(
                    "de:bund:bgb:p_823",
                    "[BGB | § 823 | Deliktische Verschuldenshaftung]",
                    "(1) Wer vorsätzlich oder fahrlässig das Leben, den Körper, die Gesundheit, die Freiheit, das Eigentum oder ein sonstiges Recht eines anderen widerrechtlich verletzt, ist dem anderen zum Ersatz des daraus entstehenden Schadens verpflichtet.",
                    date(1900, 1, 1),
                )
            ],
        ),
        (
            NormUnit(
                norm_id="de:bund:stvg:p_7",
                act_id="de:bund:stvg",
                eli_uri="eli/bund/bgbl-1/2003/s310/p_7",
                designation="§ 7",
                heading="Haftung des Halters, Schwarzfahrt",
                hierarchy_rank=int(HierarchyRank.BUNDESRECHT),
                legal_domain="Verkehrsrecht",
            ),
            [
                _make_version(
                    "de:bund:stvg:p_7",
                    "[StVG | § 7 | Gefährdungshaftung als lex specialis]",
                    "(1) Wird bei dem Betrieb eines Kraftfahrzeugs ein Mensch getötet oder eine Sache beschädigt, so ist der Halter verpflichtet, dem Verletzten den daraus entstehenden Schaden auch ohne Verschulden zu ersetzen; dies gilt als gewollte Spezialregelung (lex specialis) neben § 823 BGB.",
                    date(2003, 3, 5),
                )
            ],
        ),
    ]

    chunk_count = 0
    for norm, versions in norm_specs:
        storage.upsert_norm(norm)
        parent_act = storage.get_act(norm.act_id)
        src_url = parent_act.source_url if parent_act else ""
        for ver in versions:
            storage.upsert_temporal_version(ver)
            chunks = chunk_temporal_version(ver, embedder=embedder)
            storage.upsert_chunks(chunks, source_url=src_url)
            chunk_count += len(chunks)

    decisions = [
        CourtDecision(
            decision_id="case:bverfg_1_bvr_2656_18",
            ecli="ECLI:DE:BVERFG:2021:rs20210324.1bvr265618",
            court_level=CourtLevel.BVERFG,
            court_name="Bundesverfassungsgericht (1. Senat)",
            decision_date=date(2021, 3, 24),
            file_number="1 BvR 2656/18",
            leitsatz="Aus Art. 20a GG folgt die Pflicht zum Klimaschutz; die Grundrechte sichern intertemporale Freiheit vor einseitigen Belastungsverschiebungen in die Zukunft.",
            tenor="Die Regelungen über die Reduktionspfade ab 2031 verletzen Freiheitsrechte mangels hinreichender Fortschreibung.",
            full_text=(
                "Aus Art. 20a GG folgt die verfassungsrechtliche Pflicht zum Klimaschutz. "
                "Die Grundrechte schützen als intertemporale Freiheitssicherung davor, dass "
                "Reduktionslasten unverhältnismäßig auf künftige Zeiträume verlagert werden."
            ),
            source_url="https://www.rechtsprechung-im-internet.de/jportal/?quelle=jlink&docid=KVRE417362101",
        ),
        CourtDecision(
            decision_id="case:bverfg_1_bvf_1_23",
            ecli="ECLI:DE:BVERFG:2026:vh20261012.1bvf123",
            court_level=CourtLevel.BVERFG,
            court_name="Bundesverfassungsgericht (1. Senat)",
            decision_date=date(2026, 10, 12),
            file_number="1 BvF 1/23",
            leitsatz="Verfassungsrechtliche Prüfung von Steuersätzen, Freibeträgen und der Betriebsvermögensverschonung nach § 13a und § 28a ErbStG am Maßstab des Art. 3 Abs. 1 GG.",
            tenor="Mündliche Verhandlung am 12./13. Oktober 2026 über § 13a ErbStG und § 28a ErbStG; Urteil für Frühjahr 2027 erwartet.",
            full_text=(
                "In der mündlichen Verhandlung am 12. und 13. Oktober 2026 prüfte das Bundesverfassungsgericht "
                "(Az. 1 BvF 1/23 sowie Parallelbeschwerde zu § 13a ErbStG), ob der Erlass von rund 3,7 Mrd. Euro "
                "Erbschaft- und Schenkungsteuer im Jahr 2025 über die Verschonungsbedarfsprüfung (davon ca. 3 Mrd. Euro "
                "in wenigen Großerwerben) mit dem Belastungsgleichheits- und Folgerichtigkeitsgebot des Art. 3 Abs. 1 GG vereinbar ist."
            ),
            source_url="https://www.bundesverfassungsgericht.de/",
        ),
        CourtDecision(
            decision_id="case:eugh_c_237_07",
            ecli="ECLI:EU:C:2008:447",
            court_level=CourtLevel.EUGH,
            court_name="Gerichtshof der Europäischen Union (EuGH)",
            decision_date=date(2008, 7, 25),
            file_number="C-237/07",
            leitsatz="Unmittelbar Betroffene können die Einhaltung zwingender EU-Umweltrichtlinien und Aktionspläne vor nationalen Gerichten einfordern (Anwendungsvorrang).",
            tenor="Unionsrechtliche Umweltqualitätsnormen vermitteln durchsetzbaren Rechtsschutz vor Fachgerichten.",
            full_text=(
                "Nach ständiger Rechtsprechung des EuGH genießt das Unionsrecht Anwendungsvorrang vor "
                "kollidierendem nationalem Verordnungsrecht; betroffene Bürgerinnen und Bürger sowie Umweltverbände "
                "können wirksame Aktionsprogramme im Sinne von Richtlinie 91/676/EWG gerichtlich prüfen lassen."
            ),
            source_url="https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:62007CJ0237",
        ),
        CourtDecision(
            decision_id="case:bverwg_4_cn_2_24",
            ecli="ECLI:DE:BVERWG:2024:180424U4CN2.24.0",
            court_level=CourtLevel.OBERSTES_BUNDESGERICHT,
            court_name="Bundesverwaltungsgericht (4. Senat)",
            decision_date=date(2024, 4, 18),
            file_number="4 CN 2/24",
            leitsatz="Untergesetzliche Landesverordnungen sind im Normenkontrollverfahren nach § 47 VwGO umfassend auf Vereinbarkeit mit Bundes- und Unionsrecht zu prüfen.",
            tenor="Das Oberverwaltungsgericht verwirft rechtswidrige Landesverordnungen mit allgemeinverbindlicher Wirkung.",
            full_text=(
                "Im Verfahren nach § 47 VwGO prüfen Oberverwaltungsgerichte wie das OVG Lüneburg "
                "untergesetzliche Verordnungen objektiv gegen höherrangiges Recht inklusive Europarecht."
            ),
            source_url="https://www.rechtsprechung-im-internet.de/",
        ),
    ]
    for dec in decisions:
        storage.upsert_court_decision(dec)
        d_chunks = chunk_court_decision(dec, embedder=embedder)
        storage.upsert_chunks(d_chunks, source_url=dec.source_url)
        chunk_count += len(d_chunks)

    docs = [
        ParliamentaryDoc(
            doc_id="dip:bt:21_4120",
            issuer="bundestag",
            doc_number="21/4120",
            title="Entwurf eines Gesetzes zur Reform des Wohngeldes 2026 (Stellungnahmen November 2026)",
            summary=(
                "Sachverständigen-Stellungnahmen im Bundestag im November 2026 weisen bei der Wohngeldreform auf "
                "jährliche Kürzungen von rund 2,036 Mrd. Euro ab 2028 (~40 % der Gesamtausgaben) sowie auf den "
                "drohenden Verlust gekoppelter Ansprüche auf Kinderzuschlag (§ 6a BKGG) und Bildung/Teilhabe hin."
            ),
            publication_date=date(2026, 11, 14),
            source_url="https://dip.bundestag.de/",
        ),
        ParliamentaryDoc(
            doc_id="dip:bt:20_9105",
            issuer="bundestag",
            doc_number="20/9105",
            title="Monitoring-Bericht zur Betriebsvermögensverschonung (§§ 13a, 28a ErbStG)",
            summary=(
                "Dokumentiert die Erlasse aus der Verschonungsbedarfsprüfung (ca. 3,7 Mrd. Euro in 2025) "
                "als Grundlage der teleologischen Überprüfung an Art. 3 Abs. 1 GG."
            ),
            publication_date=date(2026, 9, 30),
            source_url="https://dip.bundestag.de/",
        ),
    ]
    for doc in docs:
        storage.upsert_parliamentary_doc(doc)

    return {
        "acts": len(acts),
        "norms": len(norm_specs),
        "chunks": chunk_count,
        "decisions": len(decisions),
        "parliamentary_docs": len(docs),
    }
