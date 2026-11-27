"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Graph from "graphology";
import forceAtlas2 from "graphology-layout-forceatlas2";
import Sigma from "sigma";
import { Table2, Network } from "lucide-react";
import type { GraphEdge, GraphNode, GraphSnapshot } from "@/lib/types";

interface LegalWebGLGraphProps {
  snapshot: GraphSnapshot;
}

const LEVEL_COLORS: Record<string, string> = {
  international: "#4338CA",
  eu: "#1D4ED8",
  bund: "#0F3D5E",
  land: "#C2410C",
  kommunal: "#64748B",
  judikative: "#047857",
  unknown: "#DC2626",
};

export function LegalWebGLGraph({ snapshot }: LegalWebGLGraphProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [tableView, setTableView] = useState(false);
  const [webglUnavailable, setWebglUnavailable] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(
    snapshot.nodes[0] ?? null
  );

  const edgeByNode = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of snapshot.edges) {
      counts.set(e.source, (counts.get(e.source) ?? 0) + 1);
      counts.set(e.target, (counts.get(e.target) ?? 0) + 1);
    }
    return counts;
  }, [snapshot.edges]);

  useEffect(() => {
    if (tableView || !containerRef.current || snapshot.nodes.length === 0) {
      return;
    }

    const graph = new Graph({ multi: true });
    const nCount = Math.max(1, snapshot.nodes.length);

    snapshot.nodes.forEach((node, idx) => {
      const angle = (2 * Math.PI * idx) / nCount;
      const radius = 12 + node.hierarchy_rank * 4;
      graph.addNode(node.id, {
        label: node.label,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        size: node.has_conflict ? 14 : 9,
        color: node.has_conflict
          ? "#B91C1C"
          : (LEVEL_COLORS[node.jurisdiction_level] ?? "#334155"),
      });
    });

    snapshot.edges.forEach((edge: GraphEdge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        graph.addEdge(edge.source, edge.target, {
          size: edge.relation_type === "POTENTIAL_CONFLICT" ? 2.5 : 1.2,
          color:
            edge.relation_type === "POTENTIAL_CONFLICT"
              ? "#DC2626"
              : edge.resolved
                ? "#94A3B8"
                : "#D97706",
        });
      }
    });

    if (graph.order > 1) {
      forceAtlas2.assign(graph, {
        iterations: 60,
        settings: { gravity: 1.5, scalingRatio: 4 },
      });
    }

    let renderer: Sigma | null = null;
    try {
      renderer = new Sigma(graph, containerRef.current, {
        renderEdgeLabels: false,
        defaultNodeColor: "#0F3D5E",
        labelDensity: 0.85,
      });
      setWebglUnavailable(false);
      renderer.on("clickNode", ({ node }) => {
        const found = snapshot.nodes.find((n) => n.id === node);
        if (found) setSelectedNode(found);
      });
    } catch {
      setWebglUnavailable(true);
    }

    return () => {
      renderer?.kill();
    };
  }, [snapshot, tableView]);

  return (
    <section
      aria-label="Interaktiver Mehrebenen-Rechtsgraph"
      className="rounded-xl border border-editorial-border bg-white shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-editorial-border px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-editorial-ink">
            Bitemporaler Mehrebenen-Rechtsgraph (Stichtag {snapshot.as_of_date})
          </h2>
          <p className="text-xs text-editorial-muted">
            {snapshot.stats.nodes} Knoten · {snapshot.stats.edges} Kanten ·{" "}
            {snapshot.stats.conflicts} Konfliktknoten (Sigma.js + Graphology WebGL 2.0)
          </p>
        </div>

        <button
          type="button"
          onClick={() => setTableView((v) => !v)}
          aria-pressed={tableView}
          className="inline-flex items-center gap-2 rounded-lg border border-editorial-accent px-3 py-1.5 text-sm font-medium text-editorial-accent hover:bg-slate-50"
        >
          {tableView ? (
            <>
              <Network className="h-4 w-4" aria-hidden="true" />
              <span>WebGL-Graph anzeigen</span>
            </>
          ) : (
            <>
              <Table2 className="h-4 w-4" aria-hidden="true" />
              <span>Als semantische HTML-Tabelle anzeigen (WCAG 2.2)</span>
            </>
          )}
        </button>
      </div>

      {!tableView ? (
        <div className="grid grid-cols-1 lg:grid-cols-4">
          <div className="relative lg:col-span-3">
            <div
              ref={containerRef}
              className="h-[480px] w-full bg-slate-50"
              aria-label="WebGL Graph-Leinwand"
            />
            {webglUnavailable && (
              <div
                role="status"
                className="border-t border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
              >
                Hinweis: WebGL-Kontext in diesem Browserfenster nicht verfügbar. Nutzen Sie den
                1-Klick-Toggle oben rechts für die barrierefreie HTML-Tabelle.
              </div>
            )}
          </div>
          <aside className="border-t border-editorial-border p-4 lg:border-l lg:border-t-0">
            <h3 className="text-sm font-semibold text-editorial-ink">Ausgewählter Knoten</h3>
            {selectedNode ? (
              <dl className="mt-3 space-y-2 text-xs">
                <div>
                  <dt className="text-editorial-muted">Bezeichnung</dt>
                  <dd className="font-semibold text-editorial-ink">{selectedNode.label}</dd>
                </div>
                <div>
                  <dt className="text-editorial-muted">ID / ELI / ECLI</dt>
                  <dd className="break-all font-mono text-[11px]">{selectedNode.eli_or_ecli}</dd>
                </div>
                <div className="flex gap-4">
                  <div>
                    <dt className="text-editorial-muted">Ebene</dt>
                    <dd className="uppercase">{selectedNode.jurisdiction_level}</dd>
                  </div>
                  <div>
                    <dt className="text-editorial-muted">Stufenbau-Rang</dt>
                    <dd>{selectedNode.hierarchy_rank}</dd>
                  </div>
                </div>
                <div>
                  <dt className="text-editorial-muted">Geltungszeitraum</dt>
                  <dd>
                    {selectedNode.valid_from ?? "–"} bis {selectedNode.valid_to ?? "unbefristet"} (
                    {selectedNode.status})
                  </dd>
                </div>
                <div>
                  <dt className="text-editorial-muted">Verknüpfte Relationen</dt>
                  <dd>{edgeByNode.get(selectedNode.id) ?? 0}</dd>
                </div>
                {selectedNode.has_conflict && (
                  <p className="rounded bg-red-50 p-2 font-medium text-editorial-danger">
                    Markierter Konfliktknoten im Audit-Netzwerk
                  </p>
                )}
              </dl>
            ) : (
              <p className="mt-2 text-xs text-editorial-muted">
                Klicken Sie im Graph auf einen Knoten.
              </p>
            )}
          </aside>
        </div>
      ) : (
        <div className="overflow-x-auto p-4">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="mb-2 text-left text-xs text-editorial-muted">
              Vollständige barrierefreie Knotentabelle zum Stichtag {snapshot.as_of_date} (WCAG 2.2).
            </caption>
            <thead>
              <tr className="border-b border-editorial-border bg-slate-50 text-xs uppercase text-editorial-muted">
                <th scope="col" className="px-3 py-2">Norm / Entscheidung</th>
                <th scope="col" className="px-3 py-2">Ebene</th>
                <th scope="col" className="px-3 py-2">Rang</th>
                <th scope="col" className="px-3 py-2">Rechtsgebiet</th>
                <th scope="col" className="px-3 py-2">Status</th>
                <th scope="col" className="px-3 py-2">ELI / ECLI</th>
                <th scope="col" className="px-3 py-2">Konflikt</th>
              </tr>
            </thead>
            <tbody>
              {snapshot.nodes.map((node) => (
                <tr key={node.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <th scope="row" className="px-3 py-2 font-medium text-editorial-ink">
                    {node.label}
                  </th>
                  <td className="px-3 py-2 uppercase text-xs">{node.jurisdiction_level}</td>
                  <td className="px-3 py-2 tabular-nums">{node.hierarchy_rank}</td>
                  <td className="px-3 py-2">{node.legal_domain}</td>
                  <td className="px-3 py-2 text-xs">{node.status}</td>
                  <td className="px-3 py-2 font-mono text-xs">{node.eli_or_ecli}</td>
                  <td className="px-3 py-2">
                    {node.has_conflict ? (
                      <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-editorial-danger">
                        Konflikt
                      </span>
                    ) : (
                      <span className="text-xs text-editorial-muted">–</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
