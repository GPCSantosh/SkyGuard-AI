import React from 'react';
import { ShieldCheck, Cpu, MapPin, ClipboardList, Database } from 'lucide-react';
import { formatIsoUtc } from '../utils/formatters';

interface EvidencePanelProps {
  evidenceHierarchy?: {
    direct_evidence?: unknown;
    model_evidence?: unknown;
    contextual_evidence?: unknown;
    operational_interpretation?: unknown;
  };
  confidenceScore?: number;
  auditMetadata?: {
    model_version?: string;
    feature_version?: string;
    decision_engine_version?: string;
    explanation_method?: string;
    generated_at?: string;
    input_station_id?: string;
    input_timestamp?: string;
  };
}

/**
 * Parses unknown evidence hierarchy fields into structured, readable key-value or item pairs.
 * Strictly avoids raw JSON dumps.
 */
function parseEvidenceToEntries(evidence: unknown): Array<{ key: string; value: string }> {
  if (!evidence) return [];
  if (typeof evidence === 'string') {
    return [{ key: 'Summary', value: evidence }];
  }
  if (Array.isArray(evidence)) {
    return evidence.map((item, i) => {
      if (typeof item === 'object' && item !== null) {
        const str = Object.entries(item)
          .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'number' ? v.toFixed(2) : String(v)}`)
          .join(' | ');
        return { key: `Item ${i + 1}`, value: str };
      }
      return { key: `Point ${i + 1}`, value: String(item) };
    });
  }
  if (typeof evidence === 'object') {
    return Object.entries(evidence).map(([k, v]) => {
      let valStr = '';
      if (typeof v === 'number') {
        valStr = Number.isInteger(v) ? String(v) : v.toFixed(2);
      } else if (typeof v === 'boolean') {
        valStr = v ? 'YES / PASS' : 'NO / FAIL';
      } else if (Array.isArray(v)) {
        valStr = v.map((item) => (typeof item === 'object' ? JSON.stringify(item) : String(item))).join(', ');
      } else if (typeof v === 'object' && v !== null) {
        valStr = Object.entries(v)
          .map(([subK, subV]) => `${subK}: ${typeof subV === 'number' ? subV.toFixed(2) : String(subV)}`)
          .join(', ');
      } else {
        valStr = String(v ?? '--');
      }

      const formattedKey = k
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
      return { key: formattedKey, value: valStr };
    });
  }
  return [{ key: 'Detail', value: String(evidence) }];
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidenceHierarchy,
  confidenceScore,
  auditMetadata,
}) => {
  const direct = parseEvidenceToEntries(evidenceHierarchy?.direct_evidence);
  const model = parseEvidenceToEntries(evidenceHierarchy?.model_evidence);
  const contextual = parseEvidenceToEntries(evidenceHierarchy?.contextual_evidence);
  const operational = parseEvidenceToEntries(evidenceHierarchy?.operational_interpretation);

  return (
    <div className="p-4 rounded border border-border bg-surface-1 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2.5">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {/* Tier 1: Direct Sensor Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
              <span className="w-2 h-2 rounded-full bg-ops-weather flex-shrink-0" />
              1. Direct Sensor Evidence
            </div>
            {direct.length > 0 ? (
              <div className="space-y-1.5 font-mono text-data">
                {direct.map((item, i) => (
                  <div key={i} className="flex justify-between items-start gap-2 border-b border-border-subtle/50 pb-1">
                    <span className="text-slate-400 text-[11px]">{item.key}:</span>
                    <span className="text-slate-200 text-right text-[11px] font-medium">{item.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-[11px] text-slate-500 italic">No direct physical limit violations observed.</span>
            )}
          </div>
        </div>

        {/* Tier 2: Model Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
              <Cpu className="w-3.5 h-3.5 text-ops-pressure flex-shrink-0" />
              2. ML Model Evidence
            </div>
            {model.length > 0 ? (
              <div className="space-y-1.5 font-mono text-data">
                {model.map((item, i) => (
                  <div key={i} className="flex justify-between items-start gap-2 border-b border-border-subtle/50 pb-1">
                    <span className="text-slate-400 text-[11px]">{item.key}:</span>
                    <span className="text-slate-200 text-right text-[11px] font-medium">{item.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-[11px] text-slate-500 italic">Model scores within nominal calibrated envelope.</span>
            )}
          </div>
        </div>

        {/* Tier 3: Contextual Spatial Evidence */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
              <MapPin className="w-3.5 h-3.5 text-ops-humidity flex-shrink-0" />
              3. Contextual Spatial Evidence
            </div>
            {contextual.length > 0 ? (
              <div className="space-y-1.5 font-mono text-data">
                {contextual.map((item, i) => (
                  <div key={i} className="flex justify-between items-start gap-2 border-b border-border-subtle/50 pb-1">
                    <span className="text-slate-400 text-[11px]">{item.key}:</span>
                    <span className="text-slate-200 text-right text-[11px] font-medium">{item.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-[11px] text-slate-500 italic">Adjacent network stations confirm regional coherence.</span>
            )}
          </div>
        </div>

        {/* Tier 4: Operational Interpretation */}
        <div className="p-3 rounded bg-surface-2 border border-border-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 font-semibold uppercase tracking-wider mb-2">
              <ClipboardList className="w-3.5 h-3.5 text-ops-warning flex-shrink-0" />
              4. Operational Guidance & Rationale
            </div>
            {operational.length > 0 ? (
              <div className="space-y-1.5 font-mono text-data">
                {operational.map((item, i) => (
                  <div key={i} className="flex justify-between items-start gap-2 border-b border-border-subtle/50 pb-1">
                    <span className="text-slate-400 text-[11px]">{item.key}:</span>
                    <span className="text-slate-200 text-right text-[11px] font-medium">{item.value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-[11px] text-slate-500 italic">Nominal telemetry baseline. Standard operations apply.</span>
            )}
          </div>
        </div>
      </div>

      {/* Audit Trail & Provenance Footer */}
      {auditMetadata && (
        <div className="p-2.5 rounded bg-surface-2/60 border border-border-subtle flex flex-wrap items-center justify-between gap-3 text-[10px] font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <Database className="w-3 h-3 text-slate-500" />
            <span>Audit Trail:</span>
            <span className="text-slate-300">Model: {auditMetadata.model_version || 'isolation_forest_v1'}</span>
            <span>|</span>
            <span className="text-slate-300">Engine: {auditMetadata.decision_engine_version || 'hybrid_v1.0.0'}</span>
            <span>|</span>
            <span className="text-slate-300">Method: {auditMetadata.explanation_method || 'TREE_SHAP'}</span>
          </div>
          <div>
            Generated: {formatIsoUtc(auditMetadata.generated_at)}
          </div>
        </div>
      )}
    </div>
  );
};
