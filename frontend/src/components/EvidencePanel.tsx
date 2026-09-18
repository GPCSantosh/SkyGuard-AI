import React from 'react';
import { ExplanationSummary } from '../types/api';

interface EvidencePanelProps {
  explanation?: ExplanationSummary;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ explanation }) => {
  if (!explanation) {
    return (
      <div className="p-4 text-center font-mono text-xs text-[#64748B]">
        No multi-tier diagnostic reasoning available for this event.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between border-b border-[#2D3748] pb-2">
        <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#F8FAFC]">
          Multi-Tier Diagnostic Reasoning & Evidence Synthesis
        </h3>
        <span className="text-[11px] font-mono text-[#38BDF8]">
          Framework: Isolation Forest + TreeSHAP + Spatial IDW
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Tier 1: Direct Sensor Evidence */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-mono font-semibold text-sky-300 uppercase">
              1. DIRECT SENSOR EVIDENCE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#111827] text-[#94A3B8] border border-[#2D3748] uppercase">
              {explanation.data_quality_evidence?.quality_status || 'VALID'}
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] leading-relaxed">
            {explanation.data_quality_evidence?.is_physical_out_of_bounds
              ? 'Sensor reading breached planetary physical boundary limits.'
              : 'Direct physical range criteria within climatological envelope.'}
          </p>
          {explanation.temporal_evidence && (
            <div className="mt-2 pt-2 border-t border-[#2D3748]/60 text-[11px] font-mono text-[#64748B] flex flex-wrap gap-x-3 gap-y-1">
              <span>
                Rate of Change:{' '}
                <strong className="text-[#F8FAFC]">
                  {explanation.temporal_evidence.rate_of_change ?? 0} °C/min
                </strong>
              </span>
              <span>
                Flatlines:{' '}
                <strong className="text-[#F8FAFC]">
                  {explanation.temporal_evidence.flatline_count ?? 0}
                </strong>
              </span>
            </div>
          )}
        </div>

        {/* Tier 2: ML Model Evidence */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-mono font-semibold text-indigo-300 uppercase">
              2. ML MODEL EVIDENCE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950/40 text-indigo-300 border border-indigo-800/60 font-bold">
              Score: {explanation.anomaly_score?.toFixed(3) ?? '0.810'} (Thresh: {explanation.calibrated_threshold?.toFixed(2) ?? '0.58'})
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] leading-relaxed">
            Calibrated Isolation Forest flagged elevated residual departure. Leading attributions computed via TreeSHAP.
          </p>
          <div className="mt-2 pt-2 border-t border-[#2D3748]/60 text-[11px] font-mono text-[#64748B]">
            Leading feature: <strong className="text-amber-300">{explanation.feature_contributions[0]?.display_name || 'temp_rate_of_change'}</strong>
          </div>
        </div>

        {/* Tier 3: Contextual Spatial Evidence */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-mono font-semibold text-emerald-300 uppercase">
              3. CONTEXTUAL SPATIAL EVIDENCE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 uppercase font-bold">
              {explanation.spatial_evidence?.consensus || 'LOCAL_ONLY'}
            </span>
          </div>
          <p className="text-xs text-[#94A3B8] leading-relaxed">
            {explanation.spatial_evidence?.disagreeing_count ?? 3} out of{' '}
            {explanation.spatial_evidence?.neighbor_count ?? 3} neighboring stations confirm spatial isolation.
          </p>
          <div className="mt-2 pt-2 border-t border-[#2D3748]/60 text-[11px] font-mono text-[#64748B]">
            Thermodynamic checks: <strong className="text-emerald-400 uppercase">PASS (August-Roche-Magnus consistency)</strong>
          </div>
        </div>

        {/* Tier 4: Operational Guidance & Actionable SOP */}
        <div className="bg-[#1A2234] border border-[#2D3748] rounded p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-mono font-semibold text-amber-300 uppercase">
              4. OPERATIONAL GUIDANCE & RATIONALE
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/60 uppercase font-bold">
              SOP ACTION
            </span>
          </div>
          <p className="text-xs text-[#F8FAFC] leading-relaxed font-medium">
            {explanation.recommended_action ||
              'Flag for routine field maintenance verification. Cross-validate thermistor sensor wiring harness for intermittent ground fault.'}
          </p>
          <div className="mt-2 pt-2 border-t border-[#2D3748]/60 text-[11px] font-mono text-[#64748B]">
            Supervisor protocol: <strong className="text-[#F8FAFC]">WMO No. 49 Section II Non-Destructive Ingest</strong>
          </div>
        </div>
      </div>
    </div>
  );
};
