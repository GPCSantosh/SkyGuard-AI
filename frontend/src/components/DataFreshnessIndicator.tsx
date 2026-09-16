import React from 'react';
import { Wifi, WifiOff } from 'lucide-react';

interface DataFreshnessIndicatorProps {
  isConnected: boolean;
  secondsSinceLastUpdate: number;
  lastHeartbeat?: Date | null;
}

export const DataFreshnessIndicator: React.FC<DataFreshnessIndicatorProps> = ({
  isConnected,
  secondsSinceLastUpdate,
  lastHeartbeat,
}) => {
  let statusText = 'LIVE STREAM';
  let pulseColor = 'bg-emerald-400';
  let badgeBorder = 'border-emerald-800/80 bg-emerald-950/40 text-emerald-300';

  if (!isConnected) {
    statusText = 'OFFLINE / DISCONNECTED';
    pulseColor = 'bg-red-500';
    badgeBorder = 'border-red-800/80 bg-red-950/40 text-red-400';
  } else if (secondsSinceLastUpdate > 30) {
    statusText = `STALE (${secondsSinceLastUpdate}s)`;
    pulseColor = 'bg-amber-400';
    badgeBorder = 'border-amber-800/80 bg-amber-950/40 text-amber-300';
  }

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded text-[11px] font-mono border ${badgeBorder}`}>
      <span className="relative flex h-2 w-2">
        {isConnected && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pulseColor}`} />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${pulseColor}`} />
      </span>
      <span className="tracking-wide font-medium">{statusText}</span>
      {isConnected ? (
        <Wifi className="w-3.5 h-3.5 opacity-80" />
      ) : (
        <WifiOff className="w-3.5 h-3.5 opacity-80 text-red-400" />
      )}
      {lastHeartbeat && (
        <span className="text-slate-400 text-[10px] hidden sm:inline">
          {lastHeartbeat.toISOString().substring(11, 19)}Z
        </span>
      )}
    </div>
  );
};
