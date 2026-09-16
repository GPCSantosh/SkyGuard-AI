import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAnomalies, useAnomalyDetail, useAnomalyExplanation } from '../hooks/useAnomalies';
import { useStationHealth } from '../hooks/useStations';
import { DecisionBanner } from '../components/DecisionBanner';
import { EvidencePanel } from '../components/EvidencePanel';
import { NeighborComparison } from '../components/NeighborComparison';
import { HealthScore } from '../components/HealthScore';
import { LoadingSkeleton, ErrorState, EmptyState } from '../components/StateFeedback';
import { ArrowLeft, Cpu, Activity, CheckSquare } from 'lucide-react';

export const AnomalyInvestigationPage: React.FC = () => {
  const { eventId } = useParams<{ eventId?: string }>();
  const navigate = useNavigate();

  // If no eventId is in route, fetch recent anomalies list to select one
  const { data: allAnomalies, isLoading: isLoadingAll } = useAnomalies({ limit: 50 });
  const activeEventId = eventId || allAnomalies?.items?.[0]?.event_id;

  const { data: anomaly, isLoading: isLoadingDetail, isError: isErrorDetail } = useAnomalyDetail(activeEventId || '');
  const { data: explanation } = useAnomalyExplanation(activeEventId || '');
  const { data: stationHealth } = useStationHealth(anomaly?.station_id || '');

  if (isLoadingAll || (activeEventId && isLoadingDetail)) {
    return <LoadingSkeleton rows={8} height="h-20" />;
  }

  if (!activeEventId || !anomaly) {
    return (
      <div className="space-y-4">
        <h1 className="text-h1 font-bold font-mono text-slate-100">Anomaly Event Investigation</h1>
        <EmptyState
          title="No Anomaly Selected"
          message="Select an anomaly event from the list below or from the live monitoring stream."
        />
        {allAnomalies?.items && allAnomalies.items.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-h2 font-semibold text-slate-200">Recent Anomaly Events</h3>
            <div className="divide-y divide-border-subtle rounded border border-border bg-surface-1">
              {allAnomalies.items.map((ev) => (
                <div
                  key={ev.event_id}
                  onClick={() => navigate(`/anomalies/${ev.event_id}`)}
                  className="p-3 hover:bg-surface-2 cursor-pointer flex items-center justify-between font-mono text-data"
                >
                  <span className="font-semibold text-slate-200">{ev.event_id}</span>
                  <span className="text-slate-400">{ev.station_id}</span>
                  <span className="text-ops-weather">{ev.decision}</span>
                  <span className="text-slate-400">{ev.severity}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (isErrorDetail) {
    return (
      <ErrorState
        title={`Anomaly Event ${activeEventId} Not Found`}
        message="The requested anomaly event record could not be loaded from persistence."
        onRetry={() => navigate('/anomalies')}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Header & Event Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/network')}
            className="p-1.5 rounded hover:bg-surface-2 text-slate-400 hover:text-slate-100 transition-colors"
            title="Back to Network Overview"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-slate-400">EVENT ID:</span>
              <h1 className="text-h1 font-bold font-mono text-slate-100">{anomaly.event_id}</h1>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Station: <strong className="text-slate-200 font-mono">{anomaly.station_id}</strong> | Timestamp: {new Date(anomaly.timestamp).toUTCString()}
            </span>
          </div>
        </div>

        {/* Quick event selector dropdown */}
        {allAnomalies?.items && allAnomalies.items.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Event Switcher:</span>
            <select
              value={anomaly.event_id}
              onChange={(e) => navigate(`/anomalies/${e.target.value}`)}
              className="bg-surface-2 border border-border text-slate-200 rounded px-2.5 py-1 text-data font-mono focus:outline-none"
            >
              {allAnomalies.items.map((ev) => (
                <option key={ev.event_id} value={ev.event_id}>
                  {ev.event_id} ({ev.station_id} - {ev.severity})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 1. Flagship Decision Banner */}
      <DecisionBanner
        decision={anomaly.decision}
        severity={anomaly.severity}
        reasonCodes={anomaly.reason_codes}
        stationId={anomaly.station_id}
        timestamp={anomaly.timestamp}
        isDegradedMode={explanation?.is_degraded_mode}
      />

      {/* 2. Observed vs Recommended Comparison Row */}
      <div className="p-4 rounded border border-border bg-surface-1">
        <h3 className="text-h2 font-semibold text-slate-100 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-ops-weather" />
          Observed vs Model-Recommended Telemetry
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(anomaly.observed_values || {}).map(([param, obsVal]) => {
            const recVal = anomaly.recommended_values?.[param];
            return (
              <div key={param} className="p-3 rounded bg-surface-2 border border-border-subtle">
                <span className="text-[11px] font-mono text-slate-400 uppercase block mb-1">
                  {param.replace('_', ' ')}
                </span>
                <div className="flex items-baseline justify-between mt-1">
                  <div>
                    <span className="text-[10px] text-slate-500 block">OBSERVED</span>
                    <span className="text-h2 font-mono font-bold text-red-400">
                      {typeof obsVal === 'number' ? obsVal.toFixed(2) : '--'}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 block">RECOMMENDED</span>
                    <span className="text-h2 font-mono font-bold text-emerald-400">
                      {typeof recVal === 'number' ? recVal.toFixed(2) : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. 4-Tier Operational Evidence Hierarchy */}
      <EvidencePanel
        evidenceHierarchy={explanation?.evidence_hierarchy}
        confidenceScore={explanation?.confidence_score}
      />

      {/* 4. Model Contribution / SHAP Attribution (Ranked Table / Bar) */}
      <div className="p-4 rounded border border-border bg-surface-1">
        <div className="flex items-center justify-between mb-3 border-b border-border-subtle pb-2">
          <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-ops-pressure" />
            Model Contribution Analysis (Feature Attribution)
          </h3>
          <span className="text-[11px] font-mono text-slate-500">
            *Model contribution reflects mathematical feature impact, not causal proof.
          </span>
        </div>

        {(() => {
          const contributions = explanation?.feature_contributions || explanation?.model_contributions || [];
          if (contributions.length > 0) {
            return (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse table-dense">
                  <thead>
                    <tr className="bg-surface-2/60 border-b border-border">
                      <th className="text-[11px] font-mono text-slate-400 uppercase">Feature Name</th>
                      <th className="text-[11px] font-mono text-slate-400 uppercase text-right">Observed Value</th>
                      <th className="text-[11px] font-mono text-slate-400 uppercase text-right">Contribution Score</th>
                      <th className="text-[11px] font-mono text-slate-400 uppercase">Impact Direction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {contributions.map((feat) => {
                      const score = feat.contribution ?? feat.contribution_score ?? 0;
                      const isPositive = score > 0;
                      const dirStr = String(feat.direction).toUpperCase();
                      return (
                        <tr key={feat.feature_name} className="hover:bg-surface-2/40">
                          <td className="font-mono text-slate-200 font-semibold">{feat.feature_name}</td>
                          <td className="text-right font-mono text-slate-300">
                            {typeof feat.feature_value === 'number' ? feat.feature_value.toFixed(2) : String(feat.feature_value ?? '--')}
                          </td>
                          <td className="text-right font-mono">
                            <span className={`font-semibold ${isPositive ? 'text-red-400' : 'text-emerald-400'}`}>
                              {isPositive ? '+' : ''}{score.toFixed(3)}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-mono uppercase ${
                                dirStr.includes('INCREASE')
                                  ? 'bg-red-950 text-red-300 border border-red-800'
                                  : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              }`}
                            >
                              {dirStr.replace(/_/g, ' ')}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          }
          return (
            <div className="text-data text-slate-400 italic py-2">
              No individual feature attribution metrics recorded for this event.
            </div>
          );
        })()}
      </div>

      {/* 5. Spatial Neighbor Cross-Validation */}
      <NeighborComparison
        neighbors={explanation?.neighbor_comparison?.neighbors || explanation?.neighbor_comparisons || []}
        targetStationId={anomaly.station_id}
        targetValue={anomaly.observed_values?.temperature_c}
      />

      {/* 6. Operator Summary, Recommended SOP Actions & Health Context */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 p-4 rounded border border-border bg-surface-1 space-y-3">
          <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-ops-weather" />
            Recommended Operator Action & SOP Guidance
          </h3>
          <p className="text-data text-slate-300 bg-surface-2 p-3 rounded border border-border-subtle leading-relaxed">
            {explanation?.summary || explanation?.operator_summary || anomaly.explanation_summary}
          </p>
          {(() => {
            const steps = explanation?.recommended_investigation_steps || explanation?.recommended_actions || [];
            if (steps.length > 0) {
              return (
                <ul className="space-y-1.5 text-data text-slate-300 list-disc list-inside pt-1">
                  {steps.map((act, i) => (
                    <li key={i} className="leading-snug">{act}</li>
                  ))}
                </ul>
              );
            }
            return null;
          })()}
        </div>

        <div className="space-y-2">
          <HealthScore
            score={stationHealth?.overall_health_score ?? 100}
            band={stationHealth?.status_band ?? 'HEALTHY'}
            trend={stationHealth?.trend ?? 'STABLE'}
            showDisclaimer={true}
          />
        </div>
      </div>
    </div>
  );
};
