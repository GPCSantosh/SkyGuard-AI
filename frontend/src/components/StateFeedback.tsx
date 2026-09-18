/**
 * SkyGuard AI — State Feedback Components
 * LoadingSkeleton, EmptyState, ErrorState, DegradedModeBanner, OfflineBanner.
 */

import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number; height?: string | number }> = ({
  rows = 4,
  height = 120,
}) => {
  return (
    <div
      className="w-full bg-[#111827] border border-[#2D3748] rounded p-4 space-y-3 animate-pulse"
      style={{ minHeight: height }}
    >
      <div className="h-4 bg-[#1A2234] rounded w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3 bg-[#1A2234] rounded w-full opacity-70" />
      ))}
    </div>
  );
};

export const EmptyState: React.FC<{
  title?: string;
  message?: string;
  actionText?: string;
  onAction?: () => void;
}> = ({
  title = 'No Telemetry Available',
  message = 'No records match the selected time window or filters.',
  actionText,
  onAction,
}) => {
  return (
    <div className="w-full bg-[#111827] border border-[#2D3748] rounded p-8 text-center space-y-2">
      <div className="text-2xl text-[#64748B]">☷</div>
      <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
        {title}
      </h4>
      <p className="text-xs text-[#94A3B8] max-w-md mx-auto">{message}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-3 text-xs font-mono px-3 py-1 bg-[#1A2234] hover:bg-[#232D42] border border-[#2D3748] text-[#F8FAFC] rounded transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({
  title = 'Telemetry Ingestion Error',
  message = 'Failed to load telemetry from endpoint. Check connection or verify endpoint availability.',
  onRetry,
}) => {
  return (
    <div className="w-full bg-[#1A1010] border border-red-900/60 rounded p-4 text-left space-y-2">
      <div className="flex items-center gap-2 text-red-400 text-xs font-mono font-bold uppercase">
        <span>ERROR:</span>
        <span>{title}</span>
      </div>
      <p className="text-xs text-[#F8FAFC]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-mono text-sky-400 hover:text-sky-300 underline"
        >
          Retry Connection →
        </button>
      )}
    </div>
  );
};

export const DegradedModeBanner: React.FC<{ message?: string }> = ({
  message = 'Operating in Degraded Mode: Deterministic physics rules active. ML model inference degraded.',
}) => {
  return (
    <div className="w-full bg-amber-950/80 border-b border-amber-800 text-amber-300 px-4 py-1.5 text-xs font-mono flex items-center justify-between">
      <span className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span>{message}</span>
      </span>
      <span className="text-[10px] text-amber-400 uppercase tracking-widest font-bold">
        DEGRADED
      </span>
    </div>
  );
};

export const OfflineBanner: React.FC<{ lastTimestamp?: string }> = ({
  lastTimestamp,
}) => {
  return (
    <div className="w-full bg-[#3B1212] border-b border-red-800 text-red-200 px-4 py-1.5 text-xs font-mono flex items-center justify-between">
      <span className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        <span>
          Live telemetry stream disconnected. Viewing cached observations
          {lastTimestamp ? ` as of ${lastTimestamp}` : ''}.
        </span>
      </span>
      <span className="text-[10px] text-red-300 uppercase tracking-widest font-bold">
        OFFLINE
      </span>
    </div>
  );
};
