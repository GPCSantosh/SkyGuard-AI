import { useCallback, useEffect, useState } from 'react';
import {
  fetchActiveRunContext,
  pauseRun,
  resetRun,
  selectDataSource,
  startRun,
} from '../api/runtime';
import { DataSourceType, RunContext, RunMode } from '../types/runtime';

export function useRunContext() {
  const [context, setContext] = useState<RunContext | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshContext = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchActiveRunContext();
      setContext(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Error loading RunContext');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshContext();
    // Poll context every 5 seconds for status sync
    const interval = setInterval(refreshContext, 5000);
    return () => clearInterval(interval);
  }, [refreshContext]);

  const handleSelectSource = async (
    sourceType: DataSourceType,
    mode: RunMode,
    datasetId?: string
  ) => {
    try {
      const newCtx = await selectDataSource(sourceType, mode, datasetId);
      setContext(newCtx);
      return newCtx;
    } catch (err: any) {
      setError(err.message || 'Failed to select data source');
      throw err;
    }
  };

  const handleStart = async () => {
    const updated = await startRun();
    setContext(updated);
  };

  const handlePause = async () => {
    const updated = await pauseRun();
    setContext(updated);
  };

  const handleReset = async () => {
    const updated = await resetRun();
    setContext(updated);
  };

  return {
    context,
    loading,
    error,
    refreshContext,
    selectSource: handleSelectSource,
    startRun: handleStart,
    pauseRun: handlePause,
    resetRun: handleReset,
  };
}
