import { useState, useEffect } from 'react';
import { useSystemHealth } from './useSystem';

export interface StreamState {
  isConnected: boolean;
  isDegraded: boolean;
  lastHeartbeat: Date | null;
  secondsSinceLastUpdate: number;
  activeModelId: string;
}

export function useRealtimeStream(): StreamState {
  const { data: systemHealth, isError, dataUpdatedAt } = useSystemHealth();
  const [secondsSinceLastUpdate, setSecondsSinceLastUpdate] = useState<number>(0);

  useEffect(() => {
    const timer = setInterval(() => {
      if (dataUpdatedAt) {
        const elapsed = Math.floor((Date.now() - dataUpdatedAt) / 1000);
        setSecondsSinceLastUpdate(elapsed);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [dataUpdatedAt]);

  const isConnected = !isError && Boolean(systemHealth);
  const isDegraded = systemHealth?.status === 'DEGRADED';

  return {
    isConnected,
    isDegraded,
    lastHeartbeat: dataUpdatedAt ? new Date(dataUpdatedAt) : null,
    secondsSinceLastUpdate,
    activeModelId: systemHealth?.active_model_id || 'isolation_forest_s42',
  };
}
