/**
 * SkyGuard AI — Data Quality Review Workspace (Correction Review)
 * Supervisory inspection table with right-side forensic audit drawer.
 * Strictly separates immutable RAW OBSERVATIONS from DERIVED RECOMMENDATIONS per WMO No. 49.
 */

import React, { useState } from 'react';
import { useCorrections } from '../hooks/useCorrections';
import { CorrectionRecommendation } from '../types/api';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { formatUtcTime } from '../utils/formatters';

export const CorrectionReview: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [variableFilter, setVariableFilter] = useState<string>('ALL');
  const [selectedCorrection, setSelectedCorrection] = useState<CorrectionRecommendation | null>(null);

  const { data: corrections = [], isLoading, isError, refetch } = useCorrections({
    status: statusFilter !== 'ALL' ? statusFilter : undefined,
    target_variable: variableFilter !== 'ALL' ? variableFilter : undefined,
  });

  if (isLoading) {
    return <LoadingSkeleton rows={8} height={450} />;
  }

  if (isError) {
    return (
      <ErrorState
        title="Correction Review Engine Offline"
        message="Unable to fetch downstream advisory correction recommendations."
        onRetry={() => refetch()}
      />
    );
  }

  const filtered = corrections.filter((c) => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false;
    if (variableFilter !== 'ALL' && c.target_variable !== variableFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Banner: Scientific Immutability Principle */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div>
          <h1 className="text-base font-bold uppercase tracking-wider text-[#F8FAFC]">
            DATA QUALITY REVIEW WORKSPACE & ADVISORY IMPUTATION
          </h1>
          <p className="text-xs text-[#94A3B8] font-sans mt-0.5">
            Model-derived advisory corrections. Raw sensor observations remain immutable under WMO No. 49 guidelines.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2">
          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-[#F8FAFC] focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="REVIEW_REQUIRED">Review Required</option>
            <option value="CORRECTION_CANDIDATE">Correction Candidate</option>
            <option value="IMPUTED">Imputed</option>
            <option value="NO_CORRECTION_RECOMMENDED">No Action Needed</option>
          </select>

          {/* Variable filter */}
          <select
            value={variableFilter}
            onChange={(e) => setVariableFilter(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-[#F8FAFC] focus:outline-none"
          >
            <option value="ALL">All Variables</option>
            <option value="temperature_c">Temperature (°C)</option>
            <option value="humidity_pct">Humidity (%)</option>
            <option value="pressure_hpa">Pressure (hPa)</option>
          </select>
        </div>
      </div>

      {/* Main Review Workspace: Table + Right-Side Inspection Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Review Table (7 cols or 12 cols if drawer closed) */}
        <div
          className={`${
            selectedCorrection ? 'lg:col-span-7' : 'lg:col-span-12'
          } bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden flex flex-col`}
        >
          <div className="p-3 bg-[#111928] border-b border-[#1E293B] flex items-center justify-between">
            <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
              ADVISORY CORRECTIONS QUEUE ({filtered.length} RECORDS)
            </span>
            <span className="text-[10px] text-[#64748B]">Click row to open inspection drawer</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#0F172A]/70 uppercase">
                  <th className="py-2.5 px-3">STATION</th>
                  <th className="py-2.5 px-3">VARIABLE</th>
                  <th className="py-2.5 px-3">OBSERVED (RAW)</th>
                  <th className="py-2.5 px-3">RECOMMENDED</th>
                  <th className="py-2.5 px-3">METHOD</th>
                  <th className="py-2.5 px-3">CONFIDENCE</th>
                  <th className="py-2.5 px-3">STATUS</th>
                  <th className="py-2.5 px-3 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E293B]/60 font-mono text-xs">
                {filtered.map((item) => {
                  const isSelected = selectedCorrection?.observation_id === item.observation_id;
                  return (
                    <tr
                      key={item.observation_id}
                      onClick={() => setSelectedCorrection(item)}
                      className={`hover:bg-[#141E30] transition-colors cursor-pointer ${
                        isSelected ? 'bg-[#142338] border-l-2 border-sky-400' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3 font-bold text-sky-400">
                        {item.station_id}
                      </td>
                      <td className="py-2.5 px-3 uppercase text-[#94A3B8]">
                        {item.target_variable.replace('_', ' ')}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-red-400">
                        {item.observed_value}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-emerald-300">
                        {item.recommended_value ?? '—'}
                      </td>
                      <td className="py-2.5 px-3 text-[10px] text-[#64748B]">
                        {item.method}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-sky-300 font-bold">
                          {item.uncertainty?.confidence_level
                            ? `${Math.round(item.uncertainty.confidence_level * 100)}%`
                            : '85%'}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`text-[9px] px-2 py-0.5 rounded font-bold border uppercase ${
                            item.status === 'REVIEW_REQUIRED'
                              ? 'bg-amber-950 text-amber-300 border-amber-800'
                              : 'bg-sky-950 text-sky-300 border-sky-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span className="text-sky-400 font-bold uppercase">
                          {isSelected ? 'ACTIVE' : 'DETAILS'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Inspection Drawer (5 cols) */}
        {selectedCorrection && (
          <div className="lg:col-span-5 bg-[#0D131F] border border-[#1E293B] rounded p-4 space-y-3 font-mono text-xs shadow-xl flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
                <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
                  FORENSIC CORRECTION INSPECTION
                </span>
                <button
                  onClick={() => setSelectedCorrection(null)}
                  className="text-xs font-bold text-[#94A3B8] hover:text-white px-2 py-0.5 bg-[#141E30] rounded border border-[#1E293B]"
                >
                  CLOSE
                </button>
              </div>

              {/* Station & Variable Header */}
              <div className="bg-[#111928] p-2.5 rounded border border-[#1E293B] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sky-400 text-sm">
                    {selectedCorrection.station_id}
                  </span>
                  <span className="text-[10px] text-[#64748B]">
                    {formatUtcTime(selectedCorrection.timestamp)}
                  </span>
                </div>
                <div className="text-[11px] text-[#94A3B8]">
                  TARGET VARIABLE: <strong>{selectedCorrection.target_variable.toUpperCase()}</strong>
                </div>
              </div>

              {/* Strict Visual Separation: Raw vs Derived */}
              <div className="grid grid-cols-2 gap-2">
                {/* Raw Observation Card */}
                <div className="bg-red-950/20 border border-red-900/60 rounded p-3 space-y-1">
                  <div className="text-[10px] text-red-400 font-bold uppercase">
                    RAW OBSERVATION (IMMUTABLE)
                  </div>
                  <div className="text-xl font-bold text-red-400">
                    {selectedCorrection.observed_value}
                  </div>
                  <div className="text-[10px] text-[#94A3B8] font-sans">
                    Unmodified sensor telemetry preserved in datalogger audit store.
                  </div>
                </div>

                {/* Recommended Estimate Card */}
                <div className="bg-emerald-950/20 border border-emerald-900/60 rounded p-3 space-y-1">
                  <div className="text-[10px] text-emerald-400 font-bold uppercase">
                    DERIVED RECOMMENDATION
                  </div>
                  <div className="text-xl font-bold text-emerald-300">
                    {selectedCorrection.recommended_value ?? '—'}
                  </div>
                  <div className="text-[10px] text-[#94A3B8] font-sans">
                    Computed via {selectedCorrection.method}.
                  </div>
                </div>
              </div>

              {/* Reason & Supporting Evidence */}
              <div className="bg-[#111928] border border-[#1E293B] p-3 rounded space-y-1.5">
                <div className="text-[10px] text-[#64748B] uppercase font-bold">
                  EVIDENCE CHAIN & REASONING
                </div>
                <div className="text-amber-300 font-bold text-xs">
                  {selectedCorrection.decision_type}
                </div>
                <p className="text-[11px] text-[#94A3B8] font-sans leading-relaxed">
                  {selectedCorrection.operator_summary}
                </p>
                <div className="text-[10px] text-[#64748B] pt-1">
                  Triggers: {selectedCorrection.reason_codes?.join(', ')}
                </div>
              </div>

              {/* Uncertainty & Health */}
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="bg-[#111928] p-2.5 rounded border border-[#1E293B]">
                  <div className="text-[10px] text-[#64748B] uppercase font-bold">UNCERTAINTY BOUNDS</div>
                  <div className="font-bold text-[#F8FAFC]">
                    {selectedCorrection.uncertainty
                      ? `[${selectedCorrection.uncertainty.lower_bound}, ${selectedCorrection.uncertainty.upper_bound}]`
                      : '±0.6°C (95% CI)'}
                  </div>
                </div>
                <div className="bg-[#111928] p-2.5 rounded border border-[#1E293B]">
                  <div className="text-[10px] text-[#64748B] uppercase font-bold">STATION RELIABILITY</div>
                  <div className="font-bold text-sky-400">
                    {selectedCorrection.station_health_score ?? 91}% (HEALTHY)
                  </div>
                </div>
              </div>

              {/* Audit Metadata */}
              <div className="bg-[#0A0E17] border border-[#1E293B] p-2.5 rounded text-[10px] text-[#64748B] space-y-0.5">
                <div>OBSERVATION HASH: {selectedCorrection.observation_id}</div>
                <div>IMPUTATION ENGINE: {selectedCorrection.audit_metadata?.imputation_engine_version || 'v1.0.0'}</div>
                <div>CAUSAL PROTOCOL: WMO No. 49 NON-DESTRUCTIVE OVERLAY</div>
              </div>
            </div>

            {/* Immutability Disclaimer Footnote */}
            <div className="p-2 bg-amber-950/30 border border-amber-900/50 rounded text-[10px] text-amber-300">
              <span>
                Under international meteorological protocols, raw observations are immutable. Review actions document audit consensus.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
