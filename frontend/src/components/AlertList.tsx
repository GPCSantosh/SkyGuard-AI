import React from 'react';
import { AnomalyEventRecord } from '../types/api';
import { SeverityBadge } from './SeverityBadge';
import { LoadingSkeleton, EmptyState } from './StateFeedback';
import { ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AlertListProps {
  anomalies: AnomalyEventRecord[];
  isLoading?: boolean;
  limit?: number;
}

export const AlertList: React.FC<AlertListProps> = ({
  anomalies,
  isLoading = false,
  limit = 10,
}) => {
  const navigate = useNavigate();

  if (isLoading) {
    return <LoadingSkeleton rows={4} height="h-12" />;
  }

  const displayed = anomalies.slice(0, limit);

  if (displayed.length === 0) {
    return <EmptyState title="No Active Anomaly Events" message="All station sensors operating within nominal limits." />;
  }

  return (
    <div className="divide-y divide-border-subtle rounded border border-border bg-surface-1">
      {displayed.map((anom) => (
        <div
          key={anom.event_id}
          onClick={() => navigate(`/anomalies/${anom.event_id}`)}
          className="p-3 hover:bg-surface-2 cursor-pointer transition-colors flex items-center justify-between gap-3"
        >
          <div className="flex items-start gap-3">
            <SeverityBadge severity={anom.severity} />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-data font-semibold text-slate-100">
                  {anom.station_id}
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {anom.decision}
                </span>
              </div>
              <p className="text-[11px] text-slate-300 mt-0.5 line-clamp-1 max-w-xl">
                {anom.explanation_summary}
              </p>
              <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 mt-1">
                <span>{new Date(anom.timestamp).toISOString().substring(0, 19)}Z</span>
                <span>ID: {anom.event_id}</span>
              </div>
            </div>
          </div>

          <ChevronRight className="w-4 h-4 text-slate-500 flex-shrink-0" />
        </div>
      ))}
    </div>
  );
};
