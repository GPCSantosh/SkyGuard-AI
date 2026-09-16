import React from 'react';
import { AlertTriangle, DatabaseZap, RefreshCw } from 'lucide-react';

export const LoadingSkeleton: React.FC<{ rows?: number; height?: string }> = ({
  rows = 4,
  height = 'h-8',
}) => {
  return (
    <div className="space-y-2 animate-pulse w-full">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={`w-full ${height} bg-surface-2/60 rounded border border-border-subtle`}
        />
      ))}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({
  title = 'Service Communication Error',
  message = 'Failed to fetch telemetry data from backend API.',
  onRetry,
}) => {
  return (
    <div className="p-6 rounded border border-red-900/50 bg-red-950/20 text-center my-4">
      <div className="inline-flex p-3 rounded bg-red-950/80 border border-red-800 text-red-400 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-h2 font-semibold text-slate-100">{title}</h3>
      <p className="text-data text-slate-400 mt-1 max-w-md mx-auto">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded bg-surface-2 hover:bg-surface-hover text-slate-200 border border-border text-data font-medium transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry Request
        </button>
      )}
    </div>
  );
};

export const EmptyState: React.FC<{
  title?: string;
  message?: string;
}> = ({
  title = 'No Telemetry Available',
  message = 'No records match the selected operational filters or time window.',
}) => {
  return (
    <div className="p-8 rounded border border-border-subtle bg-surface-1 text-center my-4">
      <div className="inline-flex p-3 rounded bg-surface-2 text-slate-400 mb-3">
        <DatabaseZap className="w-6 h-6" />
      </div>
      <h3 className="text-h2 font-semibold text-slate-200">{title}</h3>
      <p className="text-data text-slate-400 mt-1 max-w-md mx-auto">{message}</p>
    </div>
  );
};

export const DegradedModeBanner: React.FC = () => {
  return (
    <div className="px-4 py-2 bg-amber-950/60 border-b border-amber-800 text-amber-300 text-data flex items-center gap-2">
      <AlertTriangle className="w-4 h-4 flex-shrink-0" />
      <span>
        <strong>Degraded Operational Mode:</strong> AI ML model inference unavailable — operating in rule-based fallback mode.
      </span>
    </div>
  );
};
