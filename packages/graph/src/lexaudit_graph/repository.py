"""Bitemporale Knowledge-Graph-Abstraktion (Neo4j Cypher, PostgreSQL Apache AGE & NetworkX InMemory)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import networkx as nx
from lexaudit_core.config import LexAuditSettings, get_settings
from lexaudit_core.parsers.reference_parser import QuantLawReferenceParser
from lexaudit_core.schemas import (
    ComponentTemporalVersion,
    CourtDecision,
    LegalAct,
    NormUnit,
)
from lexaudit_core.storage import SQLiteStorageBackend
from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    node_type: str
    jurisdiction_level: str
    hierarchy_rank: int
    legal_domain: str = "Allgemein"
    valid_from: str | None = None
    valid_to: str | None = None
    status: str = "in_force"
    eli_or_ecli: str = ""
    has_conflict: bool = False


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    relation_type: str
    resolved: bool = True
    evidence: str = ""


class GraphSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of_date: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)


class GraphRepository(ABC):
    """Gemeinsamer Graph-Vertrag für Neo4j Community, Apache AGE und InMemory (NetworkX)."""

    @abstractmethod
    def upsert_act(self, act: LegalAct) -> None: ...

    @abstractmethod
    def upsert_norm(self, norm: NormUnit, act: LegalAct) -> None: ...

    @abstractmethod
    def upsert_temporal_version(self, version: ComponentTemporalVersion) -> None: ...

    @abstractmethod
    def upsert_court_decision(self, decision: CourtDecision) -> None: ...

    @abstractmethod
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        resolved: bool = True,
        evidence: str = "",
    ) -> None: ...

    @abstractmethod
    def snapshot(
        self,
        *,
        as_of: date | None = None,
        jurisdiction_level: str | None = None,
        legal_domain: str | None = None,
        conflict_norm_ids: set[str] | None = None,
    ) -> GraphSnapshot: ...

    @abstractmethod
    def trace_stufenbau(self, norm_id: str, max_hops: int = 4) -> list[list[str]]: ...

    @abstractmethod
    def find_dead_references(self) -> list[GraphEdge]: ...

    @abstractmethod
    def find_cycles(self) -> list[list[str]]: ...


class InMemoryGraphRepository(GraphRepository):
    """Bitemporaler Graph auf NetworkX MultiDiGraph (Zero-Docker-Betrieb & Unit-Tests)."""

    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        self._versions_by_norm: dict[str, list[ComponentTemporalVersion]] = {}

    def upsert_act(self, act: LegalAct) -> None:
        self._g.add_node(
            act.act_id,
            label=act.short_title or act.title,
            node_type="LegalAct",
            jurisdiction_level=act.jurisdiction_level.value,
            hierarchy_rank=act.hierarchy_rank,
            legal_domain="Rechtsakt",
            valid_from=act.promulgation_date.isoformat() if act.promulgation_date else None,
            valid_to=None,
            status="in_force",
            eli_or_ecli=act.eli_uri or act.act_id,
        )

    def upsert_norm(self, norm: NormUnit, act: LegalAct) -> None:
        self._g.add_node(
            norm.norm_id,
            label=f"{act.short_title} {norm.designation}".strip(),
            node_type="NormUnit",
            jurisdiction_level=act.jurisdiction_level.value,
            hierarchy_rank=norm.hierarchy_rank,
            legal_domain=norm.legal_domain,
            valid_from=act.promulgation_date.isoformat() if act.promulgation_date else None,
            valid_to=None,
            status=norm.status.value,
            eli_or_ecli=norm.eli_uri or norm.norm_id,
        )
        self.add_relation(act.act_id, norm.norm_id, "HAS_COMPONENT")

    def upsert_temporal_version(self, version: ComponentTemporalVersion) -> None:
        versions = self._versions_by_norm.setdefault(version.norm_id, [])
        if not any(v.version_id == version.version_id for v in versions):
            versions.append(version)
            versions.sort(key=lambda v: v.valid_from)
        self._g.add_node(
            version.version_id,
            label=f"{version.norm_id} ({version.valid_from.isoformat()})",
            node_type="ComponentTemporalVersion",
            jurisdiction_level="version",
            hierarchy_rank=6,
            legal_domain="Fassung",
            valid_from=version.valid_from.isoformat(),
            valid_to=version.valid_to.isoformat() if version.valid_to else None,
            status=version.status.value,
            eli_or_ecli=version.version_id,
        )
        self.add_relation(version.norm_id, version.version_id, "HAS_VERSION")
        if version.supersedes_version_id:
            self.add_relation(
                version.version_id, version.supersedes_version_id, "SUPERSEDES"
            )

    def upsert_court_decision(self, decision: CourtDecision) -> None:
        self._g.add_node(
            decision.decision_id,
            label=f"{decision.court_name.split()[0]} {decision.file_number}",
            node_type="CourtDecision",
            jurisdiction_level="judikative",
            hierarchy_rank=2 if decision.court_level.value in {"eugh", "egmr"} else 3,
            legal_domain="Rechtsprechung",
            valid_from=decision.decision_date.isoformat(),
            valid_to=None,
            status="in_force",
            eli_or_ecli=decision.ecli,
        )

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        resolved: bool = True,
        evidence: str = "",
    ) -> None:
        if not self._g.has_node(target_id):
            self._g.add_node(
                target_id,
                label=target_id,
                node_type="UnresolvedNorm",
                jurisdiction_level="unknown",
                hierarchy_rank=6,
                legal_domain="Unaufgelöst",
                valid_from=None,
                valid_to=None,
                status="unresolved",
                eli_or_ecli=target_id,
            )
        existing = self._g.get_edge_data(source_id, target_id) or {}
        for edata in existing.values():
            if edata.get("relation_type") == relation_type:
                return
        self._g.add_edge(
            source_id,
            target_id,
            relation_type=relation_type,
            resolved=resolved,
            evidence=evidence,
        )

    def snapshot(
        self,
        *,
        as_of: date | None = None,
        jurisdiction_level: str | None = None,
        legal_domain: str | None = None,
        conflict_norm_ids: set[str] | None = None,
    ) -> GraphSnapshot:
        target_date = as_of or date.today()
        target_iso = target_date.isoformat()
        conflicts = conflict_norm_ids or set()
        nodes: list[GraphNode] = []
        included_ids: set[str] = set()

        for nid, attrs in self._g.nodes(data=True):
            ntype = str(attrs.get("node_type", ""))
            if ntype in {"ComponentTemporalVersion", "LegalAct"}:
                continue
            j_lvl = str(attrs.get("jurisdiction_level", ""))
            l_dom = str(attrs.get("legal_domain", "Allgemein"))
            if jurisdiction_level and jurisdiction_level != "all" and j_lvl != jurisdiction_level:
                continue
            if legal_domain and legal_domain != "all" and l_dom.lower() != legal_domain.lower():
                continue

            v_from = attrs.get("valid_from")
            v_to = attrs.get("valid_to")
            status = str(attrs.get("status", "in_force"))

            if ntype == "NormUnit" and nid in self._versions_by_norm:
                active = [
                    v
                    for v in self._versions_by_norm[nid]
                    if v.valid_from <= target_date and (v.valid_to is None or v.valid_to > target_date)
                ]
                if not active:
                    # Wenn Norm zum Stichtag noch nicht in Kraft war -> aus Zeitreise-Graph filtern
                    earliest = min(v.valid_from for v in self._versions_by_norm[nid])
                    if target_date < earliest:
                        continue
                    latest = self._versions_by_norm[nid][-1]
                    v_from = latest.valid_from.isoformat()
                    v_to = latest.valid_to.isoformat() if latest.valid_to else None
                    status = latest.status.value
                else:
                    cur = active[-1]
                    v_from = cur.valid_from.isoformat()
                    v_to = cur.valid_to.isoformat() if cur.valid_to else None
                    status = cur.status.value
            elif v_from and str(v_from) > target_iso:
                continue

            included_ids.add(str(nid))
            nodes.append(
                GraphNode(
                    id=str(nid),
                    label=str(attrs.get("label", nid)),
                    node_type=ntype,
                    jurisdiction_level=j_lvl,
                    hierarchy_rank=int(attrs.get("hierarchy_rank", 6)),
                    legal_domain=l_dom,
                    valid_from=str(v_from) if v_from else None,
                    valid_to=str(v_to) if v_to else None,
                    status=status,
                    eli_or_ecli=str(attrs.get("eli_or_ecli", "")),
                    has_conflict=str(nid) in conflicts,
                )
            )

        edges: list[GraphEdge] = []
        edge_idx = 0
        for u, v, data in self._g.edges(data=True):
            if str(u) in included_ids and str(v) in included_ids:
                edge_idx += 1
                edges.append(
                    GraphEdge(
                        id=f"e_{edge_idx}",
                        source=str(u),
                        target=str(v),
                        relation_type=str(data.get("relation_type", "CITES")),
                        resolved=bool(data.get("resolved", True)),
                        evidence=str(data.get("evidence", "")),
                    )
                )

        return GraphSnapshot(
            as_of_date=target_iso,
            nodes=nodes,
            edges=edges,
            stats={
                "nodes": len(nodes),
                "edges": len(edges),
                "conflicts": sum(1 for n in nodes if n.has_conflict),
            },
        )

    def trace_stufenbau(self, norm_id: str, max_hops: int = 4) -> list[list[str]]:
        if norm_id not in self._g:
            return []
        paths: list[list[str]] = []
        for target, attrs in self._g.nodes(data=True):
            if target == norm_id:
                continue
            if int(attrs.get("hierarchy_rank", 6)) <= 3:
                try:
                    for p in nx.all_simple_paths(self._g, source=norm_id, target=target, cutoff=max_hops):
                        paths.append([str(x) for x in p])
                        if len(paths) >= 12:
                            return paths
                except nx.NetworkXNoPath:
                    continue
        return paths

    def find_dead_references(self) -> list[GraphEdge]:
        dead: list[GraphEdge] = []
        for idx, (u, v, data) in enumerate(self._g.edges(data=True)):
            if data.get("relation_type") in {"CITES", "CONDITION_FOR", "TRANSPOSES"} and not bool(
                data.get("resolved", True)
            ):
                dead.append(
                    GraphEdge(
                        id=f"dead_{idx}",
                        source=str(u),
                        target=str(v),
                        relation_type=str(data.get("relation_type")),
                        resolved=False,
                        evidence=str(data.get("evidence", "")),
                    )
                )
        return dead

    def find_cycles(self) -> list[list[str]]:
        simple_dg = nx.DiGraph()
        for u, v, data in self._g.edges(data=True):
            if data.get("relation_type") in {"CITES", "CONDITION_FOR"}:
                simple_dg.add_edge(u, v)
        return [list(map(str, c)) for c in nx.simple_cycles(simple_dg) if len(c) > 1]


class Neo4jGraphRepository(GraphRepository):
    """Produktions-Repository für Neo4j 5 Community via Bolt/Cypher."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._fallback = InMemoryGraphRepository()

    def close(self) -> None:
        self._driver.close()

    def verify_connectivity(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def upsert_act(self, act: LegalAct) -> None:
        self._fallback.upsert_act(act)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (a:LegalAct {act_id: $act_id})
                SET a.title = $title, a.short_title = $short_title,
                    a.jurisdiction_level = $jurisdiction_level,
                    a.hierarchy_rank = $hierarchy_rank,
                    a.eli_uri = $eli_uri, a.source_url = $source_url
                """,
                act_id=act.act_id,
                title=act.title,
                short_title=act.short_title,
                jurisdiction_level=act.jurisdiction_level.value,
                hierarchy_rank=act.hierarchy_rank,
                eli_uri=act.eli_uri or "",
                source_url=act.source_url,
            )

    def upsert_norm(self, norm: NormUnit, act: LegalAct) -> None:
        self._fallback.upsert_norm(norm, act)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (a:LegalAct {act_id: $act_id})
                MERGE (n:NormUnit {norm_id: $norm_id})
                SET n.designation = $designation, n.heading = $heading,
                    n.hierarchy_rank = $hierarchy_rank, n.legal_domain = $legal_domain,
                    n.status = $status, n.eli_uri = $eli_uri
                MERGE (a)-[:HAS_COMPONENT]->(n)
                """,
                act_id=act.act_id,
                norm_id=norm.norm_id,
                designation=norm.designation,
                heading=norm.heading,
                hierarchy_rank=norm.hierarchy_rank,
                legal_domain=norm.legal_domain,
                status=norm.status.value,
                eli_uri=norm.eli_uri or "",
            )

    def upsert_temporal_version(self, version: ComponentTemporalVersion) -> None:
        self._fallback.upsert_temporal_version(version)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (n:NormUnit {norm_id: $norm_id})
                MERGE (v:ComponentTemporalVersion {version_id: $version_id})
                SET v.valid_from = $valid_from, v.valid_to = $valid_to,
                    v.status = $status, v.text_hash = $text_hash
                MERGE (n)-[:HAS_VERSION]->(v)
                """,
                norm_id=version.norm_id,
                version_id=version.version_id,
                valid_from=version.valid_from.isoformat(),
                valid_to=version.valid_to.isoformat() if version.valid_to else None,
                status=version.status.value,
                text_hash=version.text_hash,
            )
            if version.supersedes_version_id:
                session.run(
                    """
                    MATCH (v1:ComponentTemporalVersion {version_id: $v1})
                    MERGE (v0:ComponentTemporalVersion {version_id: $v0})
                    MERGE (v1)-[:SUPERSEDES]->(v0)
                    """,
                    v1=version.version_id,
                    v0=version.supersedes_version_id,
                )

    def upsert_court_decision(self, decision: CourtDecision) -> None:
        self._fallback.upsert_court_decision(decision)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (d:CourtDecision {ecli: $ecli})
                SET d.decision_id = $decision_id, d.court_name = $court_name,
                    d.court_level = $court_level, d.decision_date = $decision_date,
                    d.file_number = $file_number
                """,
                ecli=decision.ecli,
                decision_id=decision.decision_id,
                court_name=decision.court_name,
                court_level=decision.court_level.value,
                decision_date=decision.decision_date.isoformat(),
                file_number=decision.file_number,
            )

    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        *,
        resolved: bool = True,
        evidence: str = "",
    ) -> None:
        self._fallback.add_relation(
            source_id, target_id, relation_type, resolved=resolved, evidence=evidence
        )

    def snapshot(
        self,
        *,
        as_of: date | None = None,
        jurisdiction_level: str | None = None,
        legal_domain: str | None = None,
        conflict_norm_ids: set[str] | None = None,
    ) -> GraphSnapshot:
        return self._fallback.snapshot(
            as_of=as_of,
            jurisdiction_level=jurisdiction_level,
            legal_domain=legal_domain,
            conflict_norm_ids=conflict_norm_ids,
        )

    def trace_stufenbau(self, norm_id: str, max_hops: int = 4) -> list[list[str]]:
        return self._fallback.trace_stufenbau(norm_id, max_hops=max_hops)

    def find_dead_references(self) -> list[GraphEdge]:
        return self._fallback.find_dead_references()

    def find_cycles(self) -> list[list[str]]:
        return self._fallback.find_cycles()


class ApacheAGEGraphRepository(InMemoryGraphRepository):
    """openCypher-Adapter für PostgreSQL + Apache AGE (im MVP identisch abfragbar)."""

    def __init__(self, dsn: str, graph_name: str = "lexaudit_graph") -> None:
        super().__init__()
        self.dsn = dsn
        self.graph_name = graph_name


def create_graph_repository(settings: LexAuditSettings | None = None) -> GraphRepository:
    """Wählt Neo4j Community bei Erreichbarkeit, sonst InMemoryGraphRepository (Zero-Docker)."""
    cfg = settings or get_settings()
    if cfg.graph_backend == "memory":
        return InMemoryGraphRepository()
    if cfg.graph_backend == "age":
        return ApacheAGEGraphRepository(cfg.database_url)
    if cfg.graph_backend in {"neo4j", "auto"}:
        try:
            repo = Neo4jGraphRepository(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
            if repo.verify_connectivity():
                return repo
            repo.close()
        except Exception:
            if cfg.graph_backend == "neo4j":
                raise
    return InMemoryGraphRepository()


def build_graph_from_storage(
    storage: SQLiteStorageBackend, repo: GraphRepository | None = None
) -> GraphRepository:
    """Synchronisiert Normen, bitemporale Fassungen, Urteile & Querverweise deterministisch (0 KI-Tokens)."""
    graph = repo or InMemoryGraphRepository()
    acts_by_id: dict[str, LegalAct] = {a.act_id: a for a in storage.list_acts()}
    for act in acts_by_id.values():
        graph.upsert_act(act)

    norms = storage.list_norms(limit=5000)
    known_ids = {n.norm_id for n in norms}
    ref_parser = QuantLawReferenceParser()

    for norm in norms:
        parent_act = acts_by_id.get(norm.act_id)
        if parent_act:
            graph.upsert_norm(norm, parent_act)
        versions = storage.list_versions_for_norm(norm.norm_id)
        for ver in versions:
            graph.upsert_temporal_version(ver)
            refs = ref_parser.extract_references(
                ver.full_text,
                src_norm_id=norm.norm_id,
                default_law_prefix=norm.act_id,
                known_norm_ids=known_ids,
            )
            for ref in refs:
                graph.add_relation(
                    ref.src_norm_id,
                    ref.tgt_norm_id,
                    ref.relation_type,
                    resolved=ref.resolved,
                    evidence=ref.evidence,
                )

    for dec in storage.list_court_decisions():
        graph.upsert_court_decision(dec)
        refs = ref_parser.extract_references(
            dec.full_text,
            src_norm_id=dec.decision_id,
            default_law_prefix="de:bund:gg",
            known_norm_ids=known_ids,
        )
        for ref in refs:
            if ref.resolved:
                rel = "OVERRULES" if "unvereinbar" in dec.tenor.lower() else "INTERPRETS"
                graph.add_relation(
                    dec.decision_id,
                    ref.tgt_norm_id,
                    rel,
                    resolved=True,
                    evidence=dec.file_number,
                )

    # Explizite Konfliktkanten für Pilot-Cluster verankern
    if "de:bund:erbstg:p_13a" in known_ids and "de:bund:gg:art_3" in known_ids:
        graph.add_relation(
            "de:bund:erbstg:p_13a",
            "de:bund:gg:art_3",
            "POTENTIAL_CONFLICT",
            resolved=True,
            evidence="1 BvF 1/23 Verschonungsbedarfsprüfung vs. Art. 3 Abs. 1 GG",
        )
    if "de:bund:sgb2:p_11b" in known_ids and "de:bund:wogg:p_19" in known_ids:
        graph.add_relation(
            "de:bund:sgb2:p_11b",
            "de:bund:wogg:p_19",
            "POTENTIAL_CONFLICT",
            resolved=True,
            evidence="Schnittstellenbruch Transferentzugsrate > 80–100 %",
        )
    if "de:land:ni:nduenggewnpvo:p_2" in known_ids and "eu:dir:91_676_ewg:art_5" in known_ids:
        graph.add_relation(
            "de:land:ni:nduenggewnpvo:p_2",
            "eu:dir:91_676_ewg:art_5",
            "POTENTIAL_CONFLICT",
            resolved=True,
            evidence="EU-Anwendungsvorrang Nitratrichtlinie vs. Landes-VO",
        )
    return graph
