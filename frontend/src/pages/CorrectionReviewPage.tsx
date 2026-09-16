import React, { useState } from 'react';
import { useCorrections } from '../hooks/useCorrections';
import { MetricTable, ColumnDef } from '../components/MetricTable';
import { CorrectionRecommendation } from '../types/api';
import { GitCompare, ShieldAlert, Check, Info, FileText } from 'lucide-react';

export const CorrectionReviewPage: React.FC = () => {
  const [selectedObsId, setSelectedObsId] = useState<string | null>(null);
  const { data: correctionsData, isLoading } = useCorrections({ limit: 50 });

  const corrections = correctionsData?.items || [];
  const selectedCorrection = corrections.find((c) => c.observation_id === selectedObsId) || corrections[0];

  const columns: ColumnDef<CorrectionRecommendation>[] = [
    {
      key: 'station_id',
      header: 'Station',
      render: (corr) => (
        <div>
          <span className="font-mono font-bold text-slate-100">{corr.station_id}</span>
          <span className="text-[10px] text-slate-400 block">{corr.observation_id}</span>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'target_variable',
      header: 'Parameter',
      render: (corr) => (
        <span className="font-mono text-data text-ops-weather uppercase">
          {corr.target_variable.replace('_', ' ')}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'observed_value',
      header: 'Raw Observed',
      align: 'right',
      render: (corr) => (
        <span className="font-mono text-red-400 font-semibold">
          {corr.observed_value.toFixed(2)}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'recommended_value',
      header: 'Recommended',
      align: 'right',
      render: (corr) => (
        <span className="font-mono text-emerald-400 font-semibold">
          {corr.recommended_value !== null && corr.recommended_value !== undefined
            ? corr.recommended_value.toFixed(2)
            : 'N/A'}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'method',
      header: 'Estimation Method',
      render: (corr) => (
        <span className="text-[11px] font-mono text-slate-300">
          {corr.method.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'uncertainty',
      header: 'Confidence / Band',
      align: 'center',
      render: (corr) => {
        const conf = corr.uncertainty?.confidence_index;
        return (
          <span className="text-[11px] font-mono text-slate-300">
            {typeof conf === 'number' ? `${(conf * 100).toFixed(0)}%` : '--'}
          </span>
        );
      },
    },
    {
      key: 'status',
      header: 'Status',
      align: 'center',
      render: (corr) => {
        let badge = 'bg-amber-950 text-amber-300 border-amber-800';
        if (corr.status === 'CORRECTION_CANDIDATE') badge = 'bg-sky-950 text-sky-300 border-sky-800';
        if (corr.status === 'NO_CORRECTION_RECOMMENDED') badge = 'bg-slate-900 text-slate-400 border-slate-700';

        return (
          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${badge}`}>
            {corr.status.replace(/_/g, ' ')}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      {/* 1. Immutability Warning Banner (Non-dismissable) */}
      <div className="p-3.5 bg-amber-950/40 border border-amber-800/80 rounded flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="text-data text-amber-200">
          <strong className="text-slate-100 uppercase tracking-wider font-mono text-[11px] block">
            Immutable Raw Telemetry Guarantee
          </strong>
          Advisory correction recommendations are stored strictly in separate derivation partitions. Approving or reviewing a recommendation does NOT overwrite or mutate the original immutable sensor observations.
        </div>
      </div>

      {/* 2. Main Layout: Left Queue Table, Right Detail & Provenance Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column (7 cols): Correction Review Queue Table */}
        <div className="lg:col-span-7 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-ops-weather" />
              Correction Recommendation Queue ({corrections.length})
            </h2>
            <span className="text-[11px] font-mono text-slate-400">
              Human-in-the-Loop Audit Layer
            </span>
          </div>

          <MetricTable
            columns={columns}
            data={corrections}
            isLoading={isLoading}
            selectedRowId={selectedCorrection?.observation_id}
            rowIdKey="observation_id"
            onRowClick={(row) => setSelectedObsId(row.observation_id)}
            emptyMessage="No pending correction recommendations in the audit queue."
          />
        </div>

        {/* Right Column (5 cols): Recommendation Detail Drawer */}
        <div className="lg:col-span-5 space-y-4">
          {selectedCorrection ? (
            <div className="p-4 rounded border border-border bg-surface-1 space-y-4">
              <div className="flex items-center justify-between border-b border-border-subtle pb-2">
                <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-ops-weather" />
                  Recommendation Audit Inspection
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  {selectedCorrection.station_id}
                </span>
              </div>

              {/* Observed vs Recommended values */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded bg-surface-2 border border-border-subtle">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Immutable Observed</span>
                  <span className="text-stat font-mono font-bold text-red-400">
                    {selectedCorrection.observed_value.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-1">Target: {selectedCorrection.target_variable}</span>
                </div>

                <div className="p-3 rounded bg-surface-2 border border-border-subtle">
                  <span className="text-[10px] font-mono text-slate-400 uppercase block">Advisory Estimate</span>
                  <span className="text-stat font-mono font-bold text-emerald-400">
                    {selectedCorrection.recommended_value !== null && selectedCorrection.recommended_value !== undefined
                      ? selectedCorrection.recommended_value.toFixed(2)
                      : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-500 block mt-1">Method: {selectedCorrection.method}</span>
                </div>
              </div>

              {/* Uncertainty Quantification */}
              {selectedCorrection.uncertainty && (
                <div className="p-3 rounded bg-surface-2 border border-border-subtle space-y-1.5 font-mono text-[11px]">
                  <div className="flex justify-between text-slate-300">
                    <span>Plausible Range:</span>
                    <span className="text-slate-100 font-semibold">
                      [{selectedCorrection.uncertainty.estimate_range[0].toFixed(2)}, {selectedCorrection.uncertainty.estimate_range[1].toFixed(2)}]
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Supporting Neighbors:</span>
                    <span className="text-slate-100 font-semibold">{selectedCorrection.uncertainty.supporting_neighbor_count}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Method Quality:</span>
                    <span className="text-ops-weather font-semibold">{selectedCorrection.uncertainty.method_quality}</span>
                  </div>
                </div>
              )}

              {/* Operator Summary */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                  Scientific Rationale
                </span>
                <p className="text-data text-slate-300 bg-surface-2 p-3 rounded border border-border-subtle leading-relaxed">
                  {selectedCorrection.operator_summary}
                </p>
              </div>

              {/* Supporting Evidence List */}
              {selectedCorrection.supporting_evidence.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                    Supporting Evidence
                  </span>
                  <ul className="space-y-1 text-data text-slate-300 list-disc list-inside bg-surface-2 p-3 rounded border border-border-subtle">
                    {selectedCorrection.supporting_evidence.map((ev, i) => (
                      <li key={i}>{ev}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Audit Metadata */}
              <div className="p-3 rounded bg-surface-2/60 border border-border-subtle text-[10px] font-mono text-slate-400 space-y-1">
                <div>Engine: {selectedCorrection.audit_metadata?.imputation_engine_version ?? 'imputation_v1.0.0'}</div>
                <div>Causal Guarantee: {selectedCorrection.audit_metadata?.is_causal_mode ? 'STRICT ZERO-LOOKAHEAD' : 'STANDARD'}</div>
                <div>Generated: {new Date(selectedCorrection.created_at).toUTCString()}</div>
              </div>

              {/* Review Controls */}
              <div className="flex items-center gap-2 pt-2 border-t border-border-subtle">
                <button
                  onClick={() => alert(`Acknowledged advisory recommendation ${selectedCorrection.observation_id}`)}
                  className="flex-1 py-2 px-3 rounded bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 text-data font-mono font-medium flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Check className="w-4 h-4" />
                  Acknowledge Advisory
                </button>
                <button
                  onClick={() => alert(`Flagged recommendation ${selectedCorrection.observation_id} for secondary audit`)}
                  className="flex-1 py-2 px-3 rounded bg-surface-2 hover:bg-surface-hover text-slate-300 border border-border text-data font-mono font-medium flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Info className="w-4 h-4" />
                  Hold for Audit
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 rounded border border-border bg-surface-1 text-center text-slate-400 text-data">
              Select an item from the queue to view audit metadata and supporting evidence.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
