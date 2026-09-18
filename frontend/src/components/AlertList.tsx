/**
 * SkyGuard AI — Active Alert Stream Component
 * Dense operational anomaly feed sorted by severity then recency.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AnomalyEventRecord } from '../types/api';
import { SeverityBadge } from './SeverityBadge';
import { formatUtcTime, getSeverityStyle } from '../utils/formatters';

interface AlertListProps {
  alerts: AnomalyEventRecord[];
  maxVisible?: number;
  showViewAll?: boolean;
}

export const AlertList: React.FC<AlertListProps> = ({
  alerts,
  maxVisible = 6,
  showViewAll = true,
}) => {
  const navigate = useNavigate();

  const sortedAlerts = [...alerts]
    .sort((a, b) => {
      const sevOrder: Record<string, number> = {
        CRITICAL: 5,
        HIGH: 4,
        MEDIUM: 3,
        LOW: 2,
        INFO: 1,
      };
      const diff = (sevOrder[b.severity] || 0) - (sevOrder[a.severity] || 0);
      if (diff !== 0) return diff;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    })
    .slice(0, maxVisible);

  return (
    <div className="w-full bg-[#111827] border border-[#2D3748] rounded p-3 flex flex-col h-full">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#2D3748]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
            Active Anomaly Stream
          </h4>
        </div>
        {showViewAll && (
          <button
            onClick={() => navigate('/history')}
            className="text-[11px] font-mono text-sky-400 hover:text-sky-300 transition-colors"
          >
            View all →
          </button>
        )}
      </div>

      {sortedAlerts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center py-8 text-center text-xs font-mono text-[#64748B]">
          No active alerts. Network nominal.
        </div>
      ) : (
        <div className="space-y-1.5 overflow-y-auto flex-1 pr-0.5">
          {sortedAlerts.map((alert) => {
            const sevStyle = getSeverityStyle(alert.severity);

            return (
              <div
                key={alert.event_id}
                onClick={() => navigate(`/anomalies/${alert.event_id}`)}
                className={`group cursor-pointer bg-[#1A2234] hover:bg-[#232D42] border border-[#2D3748] border-l-4 ${sevStyle.accentBorder} p-2 rounded transition-all flex items-center justify-between gap-3`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    navigate(`/anomalies/${alert.event_id}`);
                  }
                }}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SeverityBadge severity={alert.severity} size="sm" />
                    <span className="font-mono text-xs font-bold text-[#F8FAFC]">
                      {alert.station_id}
                    </span>
                    <span className="text-[10px] font-mono text-[#94A3B8] px-1 bg-[#111827] border border-[#2D3748] rounded">
                      {alert.decision}
                    </span>
                  </div>
                  <div className="text-xs text-[#94A3B8] truncate mt-1">
                    {alert.explanation_summary}
                  </div>
                  <div className="text-[10px] font-mono text-[#64748B] mt-1 flex items-center gap-2">
                    <span>{formatUtcTime(alert.timestamp)}</span>
                    <span>·</span>
                    <span>ID: {alert.event_id}</span>
                  </div>
                </div>

                <div className="shrink-0 text-[#64748B] group-hover:text-sky-400 transition-colors text-sm pr-1">
                  →
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
