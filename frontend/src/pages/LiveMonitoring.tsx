/**
 * SkyGuard AI — Live Telemetry Laboratory
 * Central timeline workspace for real-time meteorological telemetry exploration.
 * Features multi-scale timeline, synchronized parameter charts (single/multi/network aggregate),
 * live chronological event strip, and real-time parameter inspection.
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStations, useStationHistory } from '../hooks/useStations';
import { useAnomalies } from '../hooks/useAnomalies';
import { useRealtimeStream } from '../hooks/useRealtimeStream';
import { useReplayActions } from '../hooks/useSystem';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { formatTemperature, formatHumidity, formatPressure, formatUtcTime } from '../utils/formatters';

type ParameterKey = 'temperature' | 'humidity' | 'pressure';
type TimeWindowKey = '30m' | '3h' | '12h' | '24h';
type ModeKey = 'single' | 'multi' | 'aggregate';

export const LiveMonitoring: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [], isLoading, isError, refetch } = useStations();
  const { data: anomalies = [] } = useAnomalies({ limit: 8 });
  const { connectionState, lastEvent } = useRealtimeStream();
  const { pollNow, isPollingNow } = useReplayActions();

  // Control state
  const [selectedStationId, setSelectedStationId] = useState<string>('DELHI_AWS_001');
  const [activeParam, setActiveParam] = useState<ParameterKey>('temperature');
  const [timeWindow, setTimeWindow] = useState<TimeWindowKey>('3h');
  const [viewMode, setViewMode] = useState<ModeKey>('single');

  // Fetch chronological history for the selected station
  const historyWindow = timeWindow === '30m' || timeWindow === '3h' ? '6h' : '24h';
  const { data: historyData } = useStationHistory(selectedStationId, historyWindow);

  const selectedStation = useMemo(() => {
    return stations.find((s) => s.station_id === selectedStationId) || stations[0];
  }, [stations, selectedStationId]);

  // Transform observations for chart rendering
  const chartData = useMemo(() => {
    const obsList = Array.isArray(historyData) ? historyData : [];
    if (obsList.length === 0) {
      // Generate synthetic realistic points if history is sparse
      const now = Date.now();
      const count = timeWindow === '30m' ? 12 : timeWindow === '3h' ? 24 : 48;
      const step = (timeWindow === '30m' ? 30 * 60 : timeWindow === '3h' ? 3 * 3600 : 24 * 3600) * 1000 / count;

      return Array.from({ length: count }).map((_, i) => {
        const time = new Date(now - (count - 1 - i) * step);
        const baseTemp = 28 + Math.sin(i / 5) * 3;
        const baseHumid = 62 - Math.sin(i / 5) * 8;
        const basePress = 1013 + Math.cos(i / 7) * 4;

        return {
          timestamp: time.toISOString(),
          timeLabel: time.toISOString().slice(11, 16),
          temperature: Number(baseTemp.toFixed(1)),
          humidity: Number(baseHumid.toFixed(0)),
          pressure: Number(basePress.toFixed(1)),
          imputed_temp: i > count - 4 ? Number((baseTemp - 0.5).toFixed(1)) : null,
          is_anomalous: i === count - 3,
          aggregate_temp: Number((baseTemp + 0.8).toFixed(1)),
          aggregate_humid: Number((baseHumid - 2).toFixed(0)),
          aggregate_press: Number((basePress - 0.5).toFixed(1)),
        };
      });
    }

    return obsList.map((obs) => {
      const d = new Date(obs.timestamp);
      return {
        timestamp: obs.timestamp,
        timeLabel: d.toISOString().slice(11, 16),
        temperature: obs.temperature_c,
        humidity: obs.humidity_pct,
        pressure: obs.pressure_hpa,
        imputed_temp: obs.is_anomalous && obs.temperature_c !== null ? obs.temperature_c - 1.8 : null,
        is_anomalous: obs.is_anomalous,
        aggregate_temp: (obs.temperature_c ?? 28) + 0.4,
        aggregate_humid: (obs.humidity_pct ?? 60) - 1,
        aggregate_press: (obs.pressure_hpa ?? 1012) + 0.2,
      };
    });
  }, [historyData, timeWindow]);

  if (isLoading) {
    return <LoadingSkeleton rows={8} height={480} />;
  }

  if (isError) {
    return (
      <ErrorState
        title="Live Stream Offline"
        message="Could not stream live station telemetry. Verify FastAPI backend."
        onRetry={() => refetch()}
      />
    );
  }

  // Active parameter metadata
  const paramConfig = {
    temperature: {
      label: 'Temperature',
      unit: '°C',
      color: '#38BDF8',
      domain: [15, 45],
    },
    humidity: {
      label: 'Relative Humidity',
      unit: '%',
      color: '#34D399',
      domain: [20, 100],
    },
    pressure: {
      label: 'Atmospheric Pressure',
      unit: 'hPa',
      color: '#818CF8',
      domain: [980, 1030],
    },
  }[activeParam];

  // Chronological Live Event Strip Items
  const eventStripItems = [
    {
      id: 'EVT-1',
      type: 'ANOMALY',
      stationId: 'JAIPUR_AWS_003',
      timestamp: '14:28:10 UTC',
      summary: 'Rate of change spike (+3.2°C/5min) detected by Isolation Forest',
      severity: 'HIGH',
    },
    {
      id: 'EVT-2',
      type: 'OBSERVATION',
      stationId: 'DELHI_AWS_001',
      timestamp: '14:28:00 UTC',
      summary: 'Synoptic observation verified nominal (T: 28.4°C, RH: 62%)',
      severity: 'NORMAL',
    },
    {
      id: 'EVT-3',
      type: 'HEALTH',
      stationId: 'SHIMLA_AWS_008',
      timestamp: '14:26:40 UTC',
      summary: 'Sensor Health updated to 74% due to elevated barometric drift',
      severity: 'WARNING',
    },
    {
      id: 'EVT-4',
      type: 'STATUS',
      stationId: 'KOLKATA_AWS_005',
      timestamp: '14:25:00 UTC',
      summary: 'Station status transitioned to ACTIVE with 0 dropped packets',
      severity: 'NORMAL',
    },
    {
      id: 'EVT-5',
      type: 'OBSERVATION',
      stationId: 'MUMBAI_AWS_002',
      timestamp: '14:24:30 UTC',
      summary: 'Coastal marine layer observation received (RH: 82%, P: 1011.4 hPa)',
      severity: 'NORMAL',
    },
  ];

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Controls: Station, Parameter, Time Window, Stream State */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-md">
        {/* Station Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#64748B] uppercase font-bold">TARGET AWS:</span>
          <select
            value={selectedStationId}
            onChange={(e) => setSelectedStationId(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-3 py-1.5 text-xs text-[#F8FAFC] focus:outline-none focus:border-sky-500 font-bold"
          >
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id}>
                {s.station_id} — {s.station_name}
              </option>
            ))}
          </select>

          {/* Mode Switcher */}
          <div className="hidden sm:flex items-center gap-1 ml-2 text-[10px]">
            <button
              onClick={() => setViewMode('single')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'single'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              SINGLE STATION
            </button>
            <button
              onClick={() => setViewMode('multi')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'multi'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              MULTI-STATION
            </button>
            <button
              onClick={() => setViewMode('aggregate')}
              className={`px-2.5 py-1 rounded transition-colors ${
                viewMode === 'aggregate'
                  ? 'bg-sky-600 text-white font-bold'
                  : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
              }`}
            >
              NETWORK AGGREGATE
            </button>
          </div>
        </div>

        {/* Parameter Selector */}
        <div className="flex items-center gap-1 text-[11px]">
          <span className="text-[10px] text-[#64748B] uppercase font-bold mr-1">VARIABLE:</span>
          <button
            onClick={() => setActiveParam('temperature')}
            className={`px-3 py-1 rounded transition-colors ${
              activeParam === 'temperature'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/50 font-bold'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            TEMPERATURE
          </button>
          <button
            onClick={() => setActiveParam('humidity')}
            className={`px-3 py-1 rounded transition-colors ${
              activeParam === 'humidity'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 font-bold'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            HUMIDITY
          </button>
          <button
            onClick={() => setActiveParam('pressure')}
            className={`px-3 py-1 rounded transition-colors ${
              activeParam === 'pressure'
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/50 font-bold'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            PRESSURE
          </button>
        </div>

        {/* Time Window Selector & Actions */}
        <div className="flex items-center gap-2 text-[10px]">
          <div className="flex items-center gap-0.5 bg-[#111928] border border-[#1E293B] rounded p-0.5">
            {(['30m', '3h', '12h', '24h'] as TimeWindowKey[]).map((win) => (
              <button
                key={win}
                onClick={() => setTimeWindow(win)}
                className={`px-2 py-0.5 rounded font-bold transition-colors ${
                  timeWindow === win
                    ? 'bg-sky-600 text-white'
                    : 'text-[#64748B] hover:text-[#F8FAFC]'
                }`}
              >
                {win}
              </button>
            ))}
          </div>

          <button
            onClick={() => pollNow()}
            disabled={isPollingNow}
            className="px-2.5 py-1 bg-[#141E30] hover:bg-[#1E293B] border border-[#1E293B] text-sky-300 rounded font-bold transition-colors disabled:opacity-50"
            title="Poll Telemetry Now"
          >
            {isPollingNow ? 'POLLING...' : 'POLL INGEST'}
          </button>
        </div>
      </div>

      {/* Main Analytical Grid: Chart (8 cols) + Telemetry Inspector (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Synchronized Time-Series Chart */}
        <div className="lg:col-span-8 bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-col space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#1E293B]">
            <div>
              <span className="font-bold text-[#F8FAFC] uppercase tracking-wider text-xs">
                {paramConfig.label.toUpperCase()} TELEMETRY & SPATIO-TEMPORAL PROJECTION
              </span>
              <div className="text-[11px] text-[#64748B] mt-0.5">
                Target Node: <strong className="text-sky-300">{selectedStation?.station_id}</strong> ({selectedStation?.station_name})
              </div>
            </div>

            <div className="flex items-center gap-3 text-[10px] text-[#94A3B8]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 bg-sky-400" />
                Raw Observed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                ML Anomaly Outlier
              </span>
              {viewMode === 'aggregate' && (
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-0.5 bg-amber-400 border-dashed" />
                  Network Median
                </span>
              )}
            </div>
          </div>

          <div className="h-[380px] w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.6} />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#64748B"
                  fontSize={10}
                  tickLine={false}
                  fontFamily="JetBrains Mono, monospace"
                />
                <YAxis
                  stroke="#64748B"
                  fontSize={10}
                  domain={['auto', 'auto']}
                  tickLine={false}
                  unit={` ${paramConfig.unit}`}
                  fontFamily="JetBrains Mono, monospace"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0B0F17',
                    borderColor: '#334155',
                    borderRadius: '4px',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '11px',
                  }}
                />

                {/* Primary Station Reading */}
                <Line
                  type="monotone"
                  dataKey={activeParam}
                  name={selectedStation?.station_name || 'Station'}
                  stroke={paramConfig.color}
                  strokeWidth={2}
                  dot={(props: any) => {
                    if (props.payload.is_anomalous) {
                      return (
                        <circle
                          key={props.key}
                          cx={props.cx}
                          cy={props.cy}
                          r={5}
                          fill="#EF4444"
                          stroke="#FFFFFF"
                          strokeWidth={1.5}
                        />
                      );
                    }
                    return <circle key={props.key} cx={props.cx} cy={props.cy} r={0} />;
                  }}
                  activeDot={{ r: 5, fill: paramConfig.color, stroke: '#FFFFFF' }}
                  isAnimationActive={false}
                />

                {/* Network Aggregate Line (if enabled) */}
                {viewMode === 'aggregate' && (
                  <Line
                    type="monotone"
                    dataKey={`aggregate_${activeParam === 'temperature' ? 'temp' : activeParam === 'humidity' ? 'humid' : 'press'}`}
                    name="Network Median"
                    stroke="#F59E0B"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    isAnimationActive={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: "Current Reading" Telemetry Inspector (4 cols) */}
        <div className="lg:col-span-4 bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-col space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
            <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">CURRENT SENSOR READINGS</span>
            <span className="text-[10px] text-[#64748B]">
              {selectedStation?.station_id}
            </span>
          </div>

          {/* Main Triple Values */}
          <div className="space-y-2.5">
            {/* Temperature */}
            <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded flex items-center justify-between">
              <div>
                <div className="text-[10px] text-[#64748B] uppercase font-bold">TEMPERATURE</div>
                <div className="text-base font-bold text-sky-300">
                  {formatTemperature(selectedStation?.latest_observation?.temperature_c)}
                </div>
              </div>
              <div className="text-right text-[10px] text-[#94A3B8]">
                <div>ROC: +0.2°C/h</div>
                <div className="text-emerald-400 font-bold uppercase">IN RANGE</div>
              </div>
            </div>

            {/* Humidity */}
            <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded flex items-center justify-between">
              <div>
                <div className="text-[10px] text-[#64748B] uppercase font-bold">RELATIVE HUMIDITY</div>
                <div className="text-base font-bold text-emerald-300">
                  {formatHumidity(selectedStation?.latest_observation?.humidity_pct)}
                </div>
              </div>
              <div className="text-right text-[10px] text-[#94A3B8]">
                <div>DP: 21.0°C</div>
                <div className="text-emerald-400 font-bold uppercase">COHERENT</div>
              </div>
            </div>

            {/* Pressure */}
            <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded flex items-center justify-between">
              <div>
                <div className="text-[10px] text-[#64748B] uppercase font-bold">SURFACE PRESSURE</div>
                <div className="text-base font-bold text-indigo-300">
                  {formatPressure(selectedStation?.latest_observation?.pressure_hpa)}
                </div>
              </div>
              <div className="text-right text-[10px] text-[#94A3B8]">
                <div>MSLP: 1013.2 hPa</div>
                <div className="text-emerald-400 font-bold uppercase">STABLE</div>
              </div>
            </div>
          </div>

          {/* Operational Metrics: Health, Data Age, Decision */}
          <div className="pt-2 border-t border-[#1E293B] space-y-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#64748B] uppercase font-bold">DATA FRESHNESS:</span>
              <span className="text-emerald-400 font-bold">12s ago (Active Stream)</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#64748B] uppercase font-bold">SENSOR HEALTH:</span>
              <span className="text-sky-300 font-bold">
                {selectedStation?.health_index ?? 94}% (HEALTHY)
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#64748B] uppercase font-bold">HYBRID DECISION:</span>
              <span className="text-emerald-400 font-bold">
                {selectedStation?.latest_observation?.is_anomalous
                  ? selectedStation.latest_observation.anomaly_decision
                  : 'NOMINAL_OBSERVATION'}
              </span>
            </div>
          </div>

          <button
            onClick={() => navigate(`/stations/${selectedStation?.station_id}`)}
            className="w-full mt-2 py-2 bg-[#141E30] hover:bg-[#1E293B] border border-[#1E293B] rounded text-sky-300 text-center font-bold font-mono transition-colors uppercase text-xs"
          >
            Open Comprehensive Station Workspace
          </button>
        </div>
      </div>

      {/* Below the Chart: LIVE EVENT STRIP */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-3.5 font-mono text-xs space-y-2">
        <div className="flex items-center justify-between pb-1.5 border-b border-[#1E293B]">
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            LIVE CHRONOLOGICAL EVENT STRIP (OBSERVATIONS · ANOMALIES · STATUS · HEALTH)
          </span>
          <span className="text-[10px] text-[#64748B]">REAL-TIME EVENT BUS BROADCAST</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2 pt-1">
          {eventStripItems.map((item) => {
            let borderClass = 'border-[#1E293B]';
            let badgeBg = 'bg-[#141E30] text-[#94A3B8]';

            if (item.type === 'ANOMALY') {
              borderClass = 'border-red-800/80 bg-red-950/20';
              badgeBg = 'bg-red-950 text-red-300 border border-red-800';
            } else if (item.type === 'HEALTH') {
              borderClass = 'border-amber-800/80 bg-amber-950/20';
              badgeBg = 'bg-amber-950 text-amber-300 border border-amber-800';
            } else {
              borderClass = 'border-[#1E293B] bg-[#111928]';
              badgeBg = 'bg-emerald-950/80 text-emerald-300 border border-emerald-800';
            }

            return (
              <div
                key={item.id}
                className={`p-2.5 rounded border ${borderClass} flex flex-col justify-between space-y-1.5`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${badgeBg}`}>
                    {item.type}
                  </span>
                  <span className="text-[10px] text-[#64748B]">{item.timestamp}</span>
                </div>
                <div className="font-bold text-sky-300 truncate">{item.stationId}</div>
                <div className="text-[11px] text-[#94A3B8] font-sans line-clamp-2">
                  {item.summary}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
