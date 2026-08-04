"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Activity, ShieldAlert, GitCommit, AlertTriangle, CheckCircle2, Terminal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/components/analyzer/i18n";

interface MatrixNode {
  id: string;
  name: string;
  type: "god_class" | "circular_dep" | "clean_module" | "high_coupling";
  loc: number;
  functions: number;
  evidenceCount: number;
  x: number;
  y: number;
}

interface MatrixEdge {
  source: string;
  target: string;
  tension: number;
  isCycle: boolean;
}

const SAMPLE_NODES: MatrixNode[] = [
  { id: "core-domain", name: "CoreDomainService.ts", type: "god_class", loc: 4280, functions: 42, evidenceCount: 6, x: 280, y: 140 },
  { id: "auth-provider", name: "AuthProvider.ts", type: "clean_module", loc: 450, functions: 8, evidenceCount: 2, x: 120, y: 80 },
  { id: "data-pipeline", name: "PipelineExecutor.py", type: "circular_dep", loc: 2150, functions: 24, evidenceCount: 5, x: 440, y: 220 },
  { id: "event-bus", name: "EventBusBroker.go", type: "high_coupling", loc: 1890, functions: 19, evidenceCount: 4, x: 200, y: 300 },
  { id: "repository-catalog", name: "RepositoryCatalog.java", type: "clean_module", loc: 820, functions: 12, evidenceCount: 3, x: 500, y: 90 },
];

const SAMPLE_EDGES: MatrixEdge[] = [
  { source: "core-domain", target: "data-pipeline", tension: 4, isCycle: true },
  { source: "data-pipeline", target: "core-domain", tension: 5, isCycle: true },
  { source: "auth-provider", target: "core-domain", tension: 2, isCycle: false },
  { source: "event-bus", target: "core-domain", tension: 3, isCycle: false },
  { source: "data-pipeline", target: "repository-catalog", tension: 1, isCycle: false },
];

export function ArchitecturalStrainMatrix() {
  const { t } = useI18n();
  const [selectedNodeId, setSelectedNodeId] = useState<string>("core-domain");
  const selectedNode = SAMPLE_NODES.find((n) => n.id === selectedNodeId) || SAMPLE_NODES[0];

  const connectedEdges = SAMPLE_EDGES.filter(
    (e) => e.source === selectedNodeId || e.target === selectedNodeId
  );

  return (
    <div className="w-full kl-paper-alt kl-border-soft rounded-lg overflow-hidden kl-font-body kl-ink shadow-sm">
      {/* Telemetry Header */}
      <div className="flex items-center justify-between px-4 py-3 kl-paper border-b kl-border-soft kl-font-mono text-xs kl-muted">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 kl-accent" />
          <span className="font-semibold kl-accent">{t("arch.matrixTitle")}</span>
          <span className="opacity-40">|</span>
          <span>{t("arch.matrixSubtitle")}</span>
        </div>
        <div className="flex items-center space-x-3">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] kl-font-mono kl-card-accent kl-danger">
            <AlertTriangle className="h-3 w-3 mr-1" /> 1 Dairesel Döngü
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] kl-font-mono kl-card-accent kl-accent">
            <Activity className="h-3 w-3 mr-1" /> Gerilim İndeksi: 0.82
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 min-h-[420px]">
        {/* Interactive Canvas (2 Columns) */}
        <div className="lg:col-span-2 relative kl-paper p-6 border-r kl-border-soft flex flex-col justify-between">
          {/* Background Grid Pattern */}
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{
              backgroundImage: `radial-gradient(var(--kl-accent) 1px, transparent 1px)`,
              backgroundSize: "24px 24px",
            }}
          />

          {/* SVG Canvas for Edges */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {SAMPLE_EDGES.map((edge, idx) => {
              const sourceNode = SAMPLE_NODES.find((n) => n.id === edge.source);
              const targetNode = SAMPLE_NODES.find((n) => n.id === edge.target);
              if (!sourceNode || !targetNode) return null;

              const isConnectedToSelected =
                edge.source === selectedNodeId || edge.target === selectedNodeId;

              return (
                <g key={idx}>
                  <line
                    x1={sourceNode.x}
                    y1={sourceNode.y}
                    x2={targetNode.x}
                    y2={targetNode.y}
                    stroke={
                      edge.isCycle
                        ? "#F59E0B"
                        : isConnectedToSelected
                        ? "#38BDF8"
                        : "#334155"
                    }
                    strokeWidth={edge.tension * (isConnectedToSelected ? 1.5 : 1)}
                    strokeDasharray={edge.isCycle ? "6 3" : undefined}
                    opacity={isConnectedToSelected ? 1 : 0.4}
                  />
                </g>
              );
            })}
          </svg>

          {/* Interactive Nodes */}
          <div className="relative w-full h-[320px]">
            {SAMPLE_NODES.map((node) => {
              const isSelected = node.id === selectedNodeId;
              const isGodClass = node.type === "god_class";
              const isCycle = node.type === "circular_dep";

              return (
                <motion.div
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  whileHover={{ scale: 1.05 }}
                  style={{ top: node.y - 20, left: node.x - 60 }}
                  className={`absolute cursor-pointer px-3 py-2 rounded border kl-font-mono text-xs transition-all shadow-md ${
                    isSelected
                      ? "kl-paper-alt border-[#C5532F] ring-2 ring-[#C5532F]/30 z-20"
                      : isGodClass
                      ? "kl-paper-alt border-[#A03A2A]/50 kl-danger z-10"
                      : isCycle
                      ? "kl-paper-alt border-[#C5532F]/50 kl-accent z-10"
                      : "kl-paper kl-border-soft kl-muted hover:border-slate-400"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    {isGodClass ? (
                      <AlertTriangle className="h-3.5 w-3.5 kl-danger" />
                    ) : isCycle ? (
                      <ShieldAlert className="h-3.5 w-3.5 kl-accent" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5 kl-success" />
                    )}
                    <span className="font-semibold tracking-tight kl-ink">{node.name}</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[10px] kl-muted">
                    <span>{node.loc} LOC</span>
                    <span className="kl-accent">{node.functions} fn</span>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center space-x-4 kl-font-mono text-[11px] kl-muted pt-2 border-t kl-border-soft z-10">
            <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-[#A03A2A] mr-1.5 inline-block" /> God Class (&gt;40 fn)</span>
            <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-[#C5532F] mr-1.5 inline-block" /> Tarjan SCC Cycle</span>
            <span className="flex items-center"><span className="w-2.5 h-2.5 rounded-full bg-[#7A8B6F] mr-1.5 inline-block" /> Clean Domain</span>
          </div>
        </div>

        {/* Diagnostic Inspector (Right Panel) */}
        <div className="kl-paper-alt p-5 kl-font-mono text-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b kl-border-soft pb-3 mb-4">
              <span className="kl-muted uppercase tracking-wider text-[10px]">{t("arch.inspectorTitle")}</span>
              <Badge variant="outline" className="border-[#C5532F] kl-accent bg-[#C5532F]/10 text-[10px]">
                {selectedNode.type.toUpperCase().replace("_", " ")}
              </Badge>
            </div>

            <h4 className="text-sm font-semibold kl-font-display kl-ink mb-1">{selectedNode.name}</h4>
            <p className="kl-muted text-[11px] mb-4">{t("arch.astNode")} <code className="kl-accent">src/core/{selectedNode.name}</code></p>

            <div className="space-y-3">
              <div className="kl-paper p-3 rounded border kl-border-soft flex justify-between items-center">
                <span className="kl-muted">{t("arch.loc")}</span>
                <span className="kl-ink font-bold">{selectedNode.loc}</span>
              </div>
              <div className="bg-paper p-3 rounded border kl-border-soft flex justify-between items-center">
                <span className="kl-muted">{t("arch.fnCount")}</span>
                <span className="kl-accent font-bold">{selectedNode.functions}</span>
              </div>
              <div className="kl-paper p-3 rounded border kl-border-soft flex justify-between items-center">
                <span className="kl-muted">{t("arch.independentEvidence")}</span>
                <span className="kl-success font-bold">{selectedNode.evidenceCount} GitHub Kaynağı</span>
              </div>
            </div>

            <div className="mt-5">
              <span className="kl-muted text-[10px] uppercase block mb-2">{t("arch.dependencyLinks")}</span>
              <div className="space-y-1.5">
                {connectedEdges.map((e, i) => (
                  <div key={i} className="flex items-center justify-between kl-paper px-2.5 py-1.5 rounded border kl-border-soft text-[11px]">
                    <span className="kl-ink">
                      {e.source === selectedNodeId ? `→ ${e.target}` : `← ${e.source}`}
                    </span>
                    {e.isCycle ? (
                      <span className="kl-danger font-semibold text-[10px]">{t("arch.circularCycle")}</span>
                    ) : (
                      <span className="kl-muted text-[10px]">Gerilim: {e.tension}/5</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t kl-border-soft mt-4">
            <Button
              className="w-full bg-[#C5532F] hover:bg-[#C5532F]/90 text-[#F2EEE3] kl-font-body font-semibold text-xs py-2"
              onClick={() => {}}
            >
              <GitCommit className="h-3.5 w-3.5 mr-1.5" /> Refactoring Planını İncele
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
