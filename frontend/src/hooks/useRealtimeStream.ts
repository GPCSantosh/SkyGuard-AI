/**
 * SkyGuard AI — Real-Time WebSocket Streaming Hook (RFC 6455)
 * Strict envelope parsing, bounded LRU deduplication, monotonic per-station ordering,
 * bounded exponential backoff with jitter, and TanStack Query cache reconciliation.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { WS_BASE_URL, USE_MOCK_DATA } from '../api/client';
import { WebSocketEnvelope, ConnectionState } from '../types/events';

// Bounded LRU deduplication capacity
const DEDUP_CAPACITY = 1000;

export function useRealtimeStream() {
  const queryClient = useQueryClient();
  const [connectionState, setConnectionState] = useState<ConnectionState>(
    USE_MOCK_DATA ? 'CONNECTED' : 'CONNECTING'
  );
  const [lastEvent, setLastEvent] = useState<WebSocketEnvelope | null>(null);
  const [lastHeartbeat, setLastHeartbeat] = useState<Date>(new Date());

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isUnmountedRef = useRef(false);

  // LRU deduplication cache
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const eventIdQueueRef = useRef<string[]>([]);

  // Per-station monotonic timestamp guard: station_id -> latest seen timestamp (ms)
  const latestStationTimestampsRef = useRef<Map<string, number>>(new Map());

  const recordEventId = useCallback((id: string): boolean => {
    if (seenEventIdsRef.current.has(id)) {
      return false; // Duplicate
    }
    seenEventIdsRef.current.add(id);
    eventIdQueueRef.current.push(id);

    if (eventIdQueueRef.current.length > DEDUP_CAPACITY) {
      const oldest = eventIdQueueRef.current.shift();
      if (oldest) seenEventIdsRef.current.delete(oldest);
    }
    return true; // New unique event
  }, []);

  const isMonotonicallyOrdered = useCallback(
    (stationId: string | null, isoTimestamp: string): boolean => {
      if (!stationId) return true;
      const msgTime = new Date(isoTimestamp).getTime();
      if (isNaN(msgTime)) return true;

      const lastTime = latestStationTimestampsRef.current.get(stationId);
      if (lastTime !== undefined && msgTime < lastTime) {
        return false; // Stale/out-of-order packet
      }
      latestStationTimestampsRef.current.set(stationId, msgTime);
      return true;
    },
    []
  );

  const resyncQueryCaches = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['stations'] });
    queryClient.invalidateQueries({ queryKey: ['anomalies'] });
    queryClient.invalidateQueries({ queryKey: ['corrections'] });
    queryClient.invalidateQueries({ queryKey: ['system'] });
    queryClient.invalidateQueries({ queryKey: ['replay'] });
  }, [queryClient]);

  const connect = useCallback(() => {
    if (USE_MOCK_DATA) {
      setConnectionState('CONNECTED');
      return;
    }

    if (isUnmountedRef.current) return;

    try {
      setConnectionState('CONNECTING');
      const ws = new WebSocket(WS_BASE_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) return;
        setConnectionState('CONNECTED');
        reconnectAttemptsRef.current = 0;
        resyncQueryCaches();
      };

      ws.onmessage = (event) => {
        if (isUnmountedRef.current) return;
        try {
          const envelope = JSON.parse(event.data) as WebSocketEnvelope;

          // Deduplication
          if (!envelope.event_id || !recordEventId(envelope.event_id)) {
            return;
          }

          // Monotonic ordering guard
          if (!isMonotonicallyOrdered(envelope.station_id, envelope.timestamp)) {
            return;
          }

          setLastEvent(envelope);
          setLastHeartbeat(new Date());

          // Targeted cache invalidation based on event type
          if (envelope.event_type === 'observation.updated') {
            queryClient.invalidateQueries({ queryKey: ['stations'] });
            if (envelope.station_id) {
              queryClient.invalidateQueries({
                queryKey: ['station', envelope.station_id],
              });
            }
          } else if (envelope.event_type === 'anomaly.created') {
            queryClient.invalidateQueries({ queryKey: ['anomalies'] });
            queryClient.invalidateQueries({ queryKey: ['stations'] });
          } else if (envelope.event_type === 'health.updated') {
            queryClient.invalidateQueries({ queryKey: ['health'] });
            queryClient.invalidateQueries({ queryKey: ['stations'] });
          } else if (envelope.event_type === 'correction.created') {
            queryClient.invalidateQueries({ queryKey: ['corrections'] });
          } else if (
            envelope.event_type === 'station.status_changed' ||
            envelope.event_type === 'system.status_changed'
          ) {
            queryClient.invalidateQueries({ queryKey: ['stations'] });
            queryClient.invalidateQueries({ queryKey: ['system'] });
          }
        } catch {
          // Non-JSON or malformed packet, ignore gracefully
        }
      };

      ws.onerror = () => {
        if (isUnmountedRef.current) return;
        setConnectionState('ERROR');
      };

      ws.onclose = () => {
        if (isUnmountedRef.current) return;
        setConnectionState('RECONNECTING');

        // Bounded exponential backoff with jitter
        const attempts = reconnectAttemptsRef.current;
        const delay =
          Math.min(30000, 1000 * Math.pow(1.5, Math.min(attempts, 8))) +
          Math.random() * 500;

        reconnectAttemptsRef.current += 1;

        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, delay);
      };
    } catch {
      setConnectionState('ERROR');
    }
  }, [recordEventId, isMonotonicallyOrdered, resyncQueryCaches]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    // Heartbeat ticker in mock mode
    let mockInterval: number | null = null;
    if (USE_MOCK_DATA) {
      mockInterval = window.setInterval(() => {
        setLastHeartbeat(new Date());
      }, 5000);
    }

    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (mockInterval) {
        clearInterval(mockInterval);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    connectionState,
    lastEvent,
    lastHeartbeat,
    isConnected: connectionState === 'CONNECTED',
    reconnect: connect,
  };
}
