import React from 'react';
import { ShieldCheck, Cpu, MapPin, ClipboardList } from 'lucide-react';

interface EvidencePanelProps {
  evidenceHierarchy?: {
    direct_evidence?: unknown;
    model_evidence?: unknown;
    contextual_evidence?: unknown;
    operational_interpretation?: unknown;
  };
  confidenceScore?: number;
}

function formatEvidenceItems(evidence: unknown): string[] {
  if (!evidence) return [];
  if (Array.isArray(evidence)) {
    return evidence.map((item) => (typeof item === 'object' && item ? JSON.stringify(item) : String(item)));
  }
  if (typeof evidence === 'object') {
    return Object.entries(evidence).map(([k, v]) => {
      if (typeof v === 'object' && v !== null) {
        return `${k.replace(/_/g, ' ')}: ${JSON.stringify(v)}`;
      }
      return `${k.replace(/_/g, ' ')}: ${v}`;
    });
  }
  return [String(evidence)];
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidenceHierarchy,
  confidenceScore,
}) => {
  const direct = formatEvidenceItems(evidenceHierarchy?.direct_evidence);
  const model = formatEvidenceItems(evidenceHierarchy?.model_evidence);
  const contextual = formatEvidenceItems(evidenceHierarchy?.contextual_evidence);
  const operational = formatEvidenceItems(evidenceHierarchy?.operational_interpretation);

  return (
    <div className="p-4 rounded border border-border bg-surface-1 space-y-4">
      <div className="flex items-center justify-between border-b border-border-subtle pb-2">
        <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-ops-weather" />
          4-Tier Operational Evidence Hierarchy
        </h3>
        {typeof confidenceScore === 'number' && (
          <span className="text-[11px] font-mono text-slate-400">
            Confidence Index: <strong className="text-slate-200">{(confidenceScore * 100).toFixed(0)}%</strong>
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Tier 1: Direct Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-ops-weather" />
            1. Direct Sensor Evidence
          </div>
          {direct.length > 0 ? (
            <ul className="space-y-1 text-data text-slate-300 list-disc list-inside">
              {direct.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          ) : (
            <span className="text-[11px] text-slate-500 italic">No direct sensor limit violations flagged.</span>
          )}
        </div>

        {/* Tier 2: Model Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
            <Cpu className="w-3.5 h-3.5 text-ops-pressure" />
            2. ML Model Evidence
          </div>
          {model.length > 0 ? (
            <ul className="space-y-1 text-data text-slate-300 list-disc list-inside">
              {model.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          ) : (
            <span className="text-[11px] text-slate-500 italic">Model score within nominal envelope.</span>
          )}
        </div>

        {/* Tier 3: Contextual Spatial Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
            <MapPin className="w-3.5 h-3.5 text-ops-humidity" />
            3. Contextual Spatial Evidence
          </div>
          {contextual.length > 0 ? (
            <ul className="space-y-1 text-data text-slate-300 list-disc list-inside">
              {contextual.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          ) : (
            <span className="text-[11px] text-slate-500 italic">Spatial neighbors corroborate current observation.</span>
          )}
        </div>

        {/* Tier 4: Operational Interpretation */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle">
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
            <ClipboardList className="w-3.5 h-3.5 text-ops-warning" />
            4. Operational SOP Guidance
          </div>
          {operational.length > 0 ? (
            <ul className="space-y-1 text-data text-slate-300 list-disc list-inside">
              {operational.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          ) : (
            <span className="text-[11px] text-slate-500 italic">No operational intervention required.</span>
          )}
        </div>
      </div>
    </div>
  );
};
