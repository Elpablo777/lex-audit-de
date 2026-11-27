"use client";

import { useMemo, useState } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GitBranch, Table2 } from "lucide-react";
import type { ConflictFinding } from "@/lib/types";

interface ConflictCausalFlowProps {
  finding: ConflictFinding;
}

export function ConflictCausalFlow({ finding }: ConflictCausalFlowProps) {
  const [showTable, setShowTable] = useState(false);

  const { nodes, edges } = useMemo(() => {
    const chainNodes: Node[] = finding.legal_chain_ids.map((id, idx) => ({
      id,
      position: { x: 40 + idx * 230, y: idx % 2 === 0 ? 40 : 140 },
      data: { label: id },
      style: {
        border: "1px solid #0F3D5E",
        borderRadius: 8,
        padding: 10,
        background: idx === 0 ? "#FEF2F2" : "#FFFFFF",
        fontSize: 12,
        width: 200,
      },
    }));

    const chainEdges: Edge[] = finding.legal_chain_ids.slice(0, -1).map((id, idx) => ({
      id: `flow-e-${idx}`,
      source: id,
      target: finding.legal_chain_ids[idx + 1]!,
      animated: true,
      label: idx === 0 ? "Kollision / Prüfung" : "Stufenbau",
    }));

    if (finding.z3_counterexample?.satisfiable) {
      const z3Id = "z3-counterexample";
      chainNodes.push({
        id: z3Id,
        position: { x: 180, y: 245 },
        data: { label: `Z3 SMT Beweis: ${finding.z3_counterexample.model_name}` },
        style: {
          border: "2px solid #B45309",
          borderRadius: 8,
          padding: 10,
          background: "#FFFBEB",
          fontSize: 12,
          width: 260,
        },
      });
      if (finding.legal_chain_ids[0]) {
        chainEdges.push({
          id: "flow-z3-edge",
          source: z3Id,
          target: finding.legal_chain_ids[0],
          label: "mathematisch bewiesen",
        });
      }
    }

    return { nodes: chainNodes, edges: chainEdges };
  }, [finding]);

  return (
    <section className="rounded-xl border border-editorial-border bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-editorial-border px-4 py-3">
        <div>
          <h2 className="text-base font-semibold text-editorial-ink">
            Konflikt- &amp; Kausalbaum (React Flow)
          </h2>
          <p className="text-xs text-editorial-muted">
            Normkette vom Ausgangskonflikt bis zum höherrangigen Prüfungsmaßstab
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          aria-pressed={showTable}
          className="inline-flex items-center gap-1.5 rounded-lg border border-editorial-accent px-3 py-1.5 text-xs font-medium text-editorial-accent hover:bg-slate-50"
        >
          {showTable ? (
            <>
              <GitBranch className="h-4 w-4" aria-hidden="true" />
              <span>Kausalbaum anzeigen</span>
            </>
          ) : (
            <>
              <Table2 className="h-4 w-4" aria-hidden="true" />
              <span>Als HTML-Tabelle anzeigen (WCAG 2.2)</span>
            </>
          )}
        </button>
      </div>

      {!showTable ? (
        <div className="h-[340px] w-full">
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      ) : (
        <div className="overflow-x-auto p-4">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="mb-2 text-left text-xs text-editorial-muted">
              Tabellarische Kausalkette zu Befund {finding.finding_id}
            </caption>
            <thead>
              <tr className="border-b border-editorial-border bg-slate-50 text-xs uppercase text-editorial-muted">
                <th scope="col" className="px-3 py-2">Schritt</th>
                <th scope="col" className="px-3 py-2">Norm / Urteil / Beweis</th>
                <th scope="col" className="px-3 py-2">Rolle im Stufenbau</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((node, idx) => (
                <tr key={node.id} className="border-b border-slate-100">
                  <td className="px-3 py-2 tabular-nums">{idx + 1}</td>
                  <th scope="row" className="px-3 py-2 font-mono text-xs">
                    {String(node.data.label)}
                  </th>
                  <td className="px-3 py-2 text-xs text-editorial-muted">
                    {node.id === "z3-counterexample"
                      ? "Formallogischer Z3-Gegenbeweis"
                      : idx === 0
                        ? "Betroffene Ausgangsnorm"
                        : "Höherrangige Vergleichs- / Kontrollnorm"}
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
