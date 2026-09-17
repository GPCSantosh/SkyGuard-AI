import React from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { ConnectionStatus } from '../types/events';

interface DataFreshnessIndicatorProps {
  isConnected: boolean;
  secondsSinceLastUpdate: number;
  lastHeartbeat?: Date | null;
  connectionStatus?: ConnectionStatus;
  transportMode?: 'WEBSOCKET' | 'POLLING';
}

export const DataFreshnessIndicator: React.FC<DataFreshnessIndicatorProps> = ({
  isConnected,
  secondsSinceLastUpdate,
  lastHeartbeat,
  connectionStatus = 'CONNECTED',
  transportMode = 'WEBSOCKET',
}) => {
  let statusText = 'LIVE STREAM · WEBSOCKET';
  let pulseColor = 'bg-emerald-400';
  let badgeBorder = 'border-emerald-800/80 bg-emerald-950/40 text-emerald-300';
  let showSpinner = false;

  if (connectionStatus === 'CONNECTED' && transportMode === 'WEBSOCKET') {
    statusText = 'LIVE STREAM · WEBSOCKET';
    pulseColor = 'bg-emerald-400';
    badgeBorder = 'border-emerald-800/80 bg-emerald-950/40 text-emerald-300';
    showSpinner = false;
  } else if (transportMode === 'POLLING' && isConnected) {
    statusText = 'LIVE STREAM · POLLING (15s)';
    pulseColor = 'bg-blue-400';
    badgeBorder = 'border-blue-800/80 bg-blue-950/40 text-blue-300';
    showSpinner = false;
  } else if (connectionStatus === 'CONNECTING' || connectionStatus === 'RECONNECTING') {
    statusText = connectionStatus === 'CONNECTING' ? 'CONNECTING WEBSOCKET...' : 'STREAM RECONNECTING...';
    pulseColor = 'bg-amber-400';
    badgeBorder = 'border-amber-800/80 bg-amber-950/40 text-amber-300';
    showSpinner = true;
  } else if (connectionStatus === 'DISCONNECTED' || connectionStatus === 'ERROR' || !isConnected) {
    statusText = 'STREAM OFFLINE / DISCONNECTED';
    pulseColor = 'bg-red-500';
    badgeBorder = 'border-red-800/80 bg-red-950/40 text-red-400';
  } else if (secondsSinceLastUpdate > 60) {
    statusText = `TELEMETRY STALE (${secondsSinceLastUpdate}s)`;
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
      {showSpinner ? (
        <RefreshCw className="w-3.5 h-3.5 opacity-80 animate-spin text-amber-400" />
      ) : isConnected ? (
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
