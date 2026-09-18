/**
 * SkyGuard AI — Anomaly Registry & Incident Queue
 * Central repository of detected meteorological and sensor anomalies with multi-criteria filtering,
 * severity badges, reason codes, and direct drilldown to forensic deep-dive investigation.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnomalies } from '../hooks/useAnomalies';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { formatUtcTime } from '../utils/formatters';

export const AnomalyRegistry: React.FC = () => {
  const navigate = useNavigate();
  const [stationFilter, setStationFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [decisionFilter, setDecisionFilter] = useState('ALL');

  const { data: anomalies = [], isLoading, isError, refetch } = useAnomalies({
    limit: 50,
  });

  if (isLoading) {
    return <LoadingSkeleton rows={8} height={450} />;
  }

  if (isError) {
    return (
      <ErrorState
        title="Anomaly Registry Error"
        message="Unable to retrieve active anomaly incident queue from backend."
        onRetry={() => refetch()}
      />
    );
  }

  const filtered = anomalies.filter((a) => {
    if (stationFilter && !a.station_id.toLowerCase().includes(stationFilter.toLowerCase())) {
      return false;
    }
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) {
      return false;
    }
    if (decisionFilter !== 'ALL' && a.decision !== decisionFilter) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Banner & Control Bar */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div>
          <h1 className="text-base font-bold uppercase tracking-wider text-[#F8FAFC]">
            ANOMALY INCIDENT QUEUE & INVESTIGATION REGISTRY
          </h1>
          <p className="text-xs text-[#94A3B8] font-sans mt-0.5">
            Traceable real-time and historical anomaly detections flagged by the hybrid decision engine.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Station Search */}
          <div className="relative w-44">
            <input
              type="text"
              placeholder="Filter station..."
              value={stationFilter}
              onChange={(e) => setStationFilter(e.target.value)}
              className="w-full bg-[#111928] border border-[#1E293B] rounded px-3 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-[#F8FAFC] focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Decision Filter */}
          <select
            value={decisionFilter}
            onChange={(e) => setDecisionFilter(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-[#F8FAFC] focus:outline-none"
          >
            <option value="ALL">All Decisions</option>
            <option value="PROBABLE_SENSOR_ANOMALY">Probable Sensor Anomaly</option>
            <option value="PROBABLE_DATA_QUALITY_ISSUE">Data Quality Issue</option>
            <option value="POSSIBLE_GENUINE_EVENT">Possible Genuine Event</option>
            <option value="UNCERTAIN">Uncertain</option>
          </select>
        </div>
      </div>

      {/* Incident Table */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#0F172A]/70 uppercase">
                <th className="py-2.5 px-3">EVENT ID</th>
                <th className="py-2.5 px-3">STATION</th>
                <th className="py-2.5 px-3">UTC TIMESTAMP</th>
                <th className="py-2.5 px-3">DECISION</th>
                <th className="py-2.5 px-3">SEVERITY</th>
                <th className="py-2.5 px-3">REASON TRIGGERS</th>
                <th className="py-2.5 px-3">OPERATOR SUMMARY</th>
                <th className="py-2.5 px-3 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]/60 font-mono text-xs">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748B]">
                    No anomaly incidents matching the selected criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((item) => {
                  const isCrit = item.severity === 'CRITICAL';
                  return (
                    <tr
                      key={item.event_id}
                      onClick={() => navigate(`/anomalies/${item.event_id}`)}
                      className="hover:bg-[#141E30] transition-colors cursor-pointer"
                    >
                      <td className="py-2.5 px-3 font-bold text-sky-400">
                        {item.event_id}
                      </td>
                      <td className="py-2.5 px-3 font-bold text-[#F8FAFC]">
                        {item.station_id}
                      </td>
                      <td className="py-2.5 px-3 text-[#94A3B8]">
                        {formatUtcTime(item.timestamp)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-[10px] text-amber-300 font-bold uppercase">
                          {item.decision}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`text-[9px] px-2 py-0.5 rounded font-bold border uppercase ${
                            isCrit
                              ? 'bg-red-950 text-red-300 border-red-800'
                              : 'bg-amber-950 text-amber-300 border-amber-800'
                          }`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[10px] text-[#64748B]">
                        {item.reason_codes?.slice(0, 2).join(', ')}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-[11px] text-[#94A3B8] max-w-xs truncate">
                        {item.explanation_summary}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/anomalies/${item.event_id}`);
                          }}
                          className="text-xs text-sky-400 hover:text-sky-200 font-sans hover:underline font-bold uppercase"
                        >
                          Triage
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
