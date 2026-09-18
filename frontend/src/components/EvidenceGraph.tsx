/**
 * SkyGuard AI — Connected Evidence Graph
 * Visualizes the 5-node forensic evidentiary chain:
 * Observation ➔ Temporal Evidence ➔ ML Evidence ➔ Spatial Evidence ➔ Final Decision
 */

import React from 'react';

interface EvidenceGraphProps {
  observationText: string;
  temporalText: string;
  mlText: string;
  spatialText: string;
  decisionText: string;
  severity: string;
}

export const EvidenceGraph: React.FC<EvidenceGraphProps> = ({
  observationText,
  temporalText,
  mlText,
  spatialText,
  decisionText,
  severity,
}) => {
  const nodes = [
    {
      step: 1,
      title: 'RAW OBSERVATION',
      desc: observationText,
      status: 'INPUT',
      color: 'border-sky-500/60 bg-sky-950/20 text-sky-300',
    },
    {
      step: 2,
      title: 'TEMPORAL INVARIANCE',
      desc: temporalText,
      status: 'VIOLATED',
      color: 'border-amber-500/60 bg-amber-950/20 text-amber-300',
    },
    {
      step: 3,
      title: 'ISOLATION FOREST (ML)',
      desc: mlText,
      status: 'OUTLIER',
      color: 'border-red-500/60 bg-red-950/20 text-red-300',
    },
    {
      step: 4,
      title: 'SPATIAL CONSENSUS',
      desc: spatialText,
      status: 'LOCAL_ONLY',
      color: 'border-indigo-500/60 bg-indigo-950/20 text-indigo-300',
    },
    {
      step: 5,
      title: 'HYBRID DECISION',
      desc: decisionText,
      status: severity,
      color: 'border-red-500 bg-red-950/40 text-red-200',
    },
  ];

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 font-mono text-xs space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
        <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
          FORENSIC EVIDENCE RELATIONSHIP GRAPH & INFERENCE FLOW
        </span>
        <span className="text-[10px] text-[#64748B]">
          CAUSAL DETERMINISTIC DECISION PIPELINE
        </span>
      </div>

      {/* Connected Nodes Ribbon */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2 relative">
        {nodes.map((node, idx) => {
          return (
            <div key={node.step} className="relative flex flex-col">
              {/* Node Card */}
              <div
                className={`flex-1 border rounded p-3 flex flex-col justify-between space-y-2 transition-all hover:border-sky-400 ${node.color}`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-[#94A3B8] font-bold">
                      STAGE 0{node.step}
                    </span>
                    <span className="text-[8px] px-1.5 py-0.2 rounded font-bold border border-current uppercase">
                      {node.status}
                    </span>
                  </div>
                  <div className="mt-1 font-bold text-xs text-[#F8FAFC]">
                    <span>{node.title}</span>
                  </div>
                </div>

                <p className="text-[11px] text-[#94A3B8] font-sans leading-relaxed">
                  {node.desc}
                </p>
              </div>

              {/* Arrow Indicator between nodes (desktop) */}
              {idx < nodes.length - 1 && (
                <div className="hidden md:flex absolute -right-2.5 top-1/2 -translate-y-1/2 z-20 font-mono text-[10px] font-bold text-sky-400 bg-[#0B0F17] px-1 border border-[#334155] rounded pointer-events-none">
                  →
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
