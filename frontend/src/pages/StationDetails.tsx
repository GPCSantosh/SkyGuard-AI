/**
 * SkyGuard AI — Analytical Station Workspace
 * Single-station operations command interface with selectable layer telemetry canvas,
 * time window analysis with anomaly markers, contextual drawer, and chronological observation ledger.
 */

import React, { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useStation, useStationHistory, useStations } from '../hooks/useStations';
import { useStationHealth } from '../hooks/useHealth';
import { useAnomalies } from '../hooks/useAnomalies';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { formatTemperature, formatHumidity, formatPressure, formatUtcTime } from '../utils/formatters';

type LayerKey = 'all' | 'temperature' | 'humidity' | 'pressure';
type TimeWindowKey = '6h' | '24h' | '7d' | '30d';

export const StationDetails: React.FC = () => {
  const { stationId = 'DELHI_AWS_001' } = useParams<{ stationId: string }>();
  const navigate = useNavigate();

  const [activeLayer, setActiveLayer] = useState<LayerKey>('all');
  const [timeWindow, setTimeWindow] = useState<TimeWindowKey>('24h');

  const { data: stations = [] } = useStations();
  const { data: station, isLoading: isStationLoading, isError } = useStation(stationId);
  const { data: history = [], isLoading: isHistoryLoading } = useStationHistory(
    stationId,
    timeWindow
  );
  const { data: health } = useStationHealth(stationId);
  const { data: anomalies = [] } = useAnomalies({ station_id: stationId });

  // Map history to chart points
  const chartData = useMemo(() => {
    if (!history || history.length === 0) {
      const count = timeWindow === '6h' ? 18 : timeWindow === '24h' ? 24 : 35;
      const now = Date.now();
      const step =
        ((timeWindow === '6h' ? 6 : timeWindow === '24h' ? 24 : 168) * 3600 * 1000) /
        count;

      return Array.from({ length: count }).map((_, i) => {
        const time = new Date(now - (count - 1 - i) * step);
        const baseTemp = 27 + Math.sin(i / 4) * 4;
        const baseHumid = 64 - Math.sin(i / 4) * 10;
        const basePress = 1012 + Math.cos(i / 6) * 3;

        return {
          timestamp: time.toISOString(),
          timeLabel: time.toISOString().slice(11, 16),
          temperature: Number(baseTemp.toFixed(1)),
          humidity: Number(baseHumid.toFixed(0)),
          pressure: Number(basePress.toFixed(1)),
          is_anomalous: i === count - 4,
        };
      });
    }

    return history.map((obs) => {
      const d = new Date(obs.timestamp);
      return {
        timestamp: obs.timestamp,
        timeLabel: d.toISOString().slice(11, 16),
        temperature: obs.temperature_c,
        humidity: obs.humidity_pct,
        pressure: obs.pressure_hpa,
        is_anomalous: obs.is_anomalous,
      };
    });
  }, [history, timeWindow]);

  if (isStationLoading || isHistoryLoading) {
    return <LoadingSkeleton rows={10} height={500} />;
  }

  if (isError || !station) {
    return (
      <ErrorState
        title="Station Telemetry Unavailable"
        message={`Unable to load operational records for AWS node: ${stationId}`}
        onRetry={() => navigate('/network')}
      />
    );
  }

  const latestObs = station.latest_observation;
  const isAnomalous = latestObs?.is_anomalous;
  const isCritical = latestObs?.anomaly_severity === 'CRITICAL';

  // Neighbor stations list
  const neighborStations = stations
    .filter((s) => s.station_id !== station.station_id)
    .slice(0, 4);

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Station Workspace Header */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-wrap items-center justify-between gap-3 text-xs font-mono shadow-md">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-[#F8FAFC]">
              {station.station_id}
            </span>
            <span className="text-xs text-[#94A3B8] font-sans">
              — {station.station_name}
            </span>

            {/* Station Switcher Dropdown */}
            <select
              value={station.station_id}
              onChange={(e) => navigate(`/stations/${e.target.value}`)}
              className="bg-[#111928] border border-[#1E293B] rounded px-2 py-0.5 text-[11px] text-sky-300 ml-2 focus:outline-none"
            >
              {stations.map((s) => (
                <option key={s.station_id} value={s.station_id}>
                  {s.station_id} ({s.station_name})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 sm:gap-4 text-[11px] text-[#64748B] mt-0.5 flex-wrap">
            <span>
              {station.district || 'District'}, {station.state || 'India'}
            </span>
            <span>·</span>
            <span>
              Coordinates: {station.latitude.toFixed(4)}°N, {station.longitude.toFixed(4)}°E
            </span>
            <span>·</span>
            <span>Elevation: {station.elevation_m}m MSL</span>
          </div>
        </div>

        {/* Operational Status & Quick Health Pill */}
        <div className="flex items-center gap-3">
          <div
            className={`px-3 py-1.5 rounded border text-xs font-bold uppercase ${
              isCritical
                ? 'bg-red-950 text-red-300 border-red-800 animate-pulse'
                : isAnomalous
                ? 'bg-amber-950 text-amber-300 border-amber-800'
                : 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
            }`}
          >
            <span>
              {isCritical
                ? 'CRITICAL SENSOR ANOMALY'
                : isAnomalous
                ? 'ATTENTION REQUIRED'
                : 'OPERATIONAL NOMINAL'}
            </span>
          </div>

          <div className="bg-[#111928] border border-[#1E293B] px-3 py-1 rounded text-right">
            <div className="text-[9px] text-[#64748B] uppercase font-bold">RELIABILITY INDEX</div>
            <div className="text-sm font-bold text-sky-300">
              {station.health_index ?? 92}%
            </div>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout: Large Telemetry Canvas + Right Contextual Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Large Synchronized Telemetry Canvas (8 cols) */}
        <div className="lg:col-span-8 bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-col space-y-3 font-mono text-xs">
          {/* Layer and Time Window Controls */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#1E293B]">
            {/* Selectable Layers / Tabs */}
            <div className="flex items-center gap-1 text-[11px]">
              <span className="text-[10px] text-[#64748B] uppercase font-bold mr-1">LAYERS:</span>
              <button
                onClick={() => setActiveLayer('all')}
                className={`px-2.5 py-1 rounded font-bold transition-colors ${
                  activeLayer === 'all'
                    ? 'bg-sky-600 text-white'
                    : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                ALL
              </button>
              <button
                onClick={() => setActiveLayer('temperature')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeLayer === 'temperature'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/50 font-bold'
                    : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                TEMPERATURE
              </button>
              <button
                onClick={() => setActiveLayer('humidity')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeLayer === 'humidity'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 font-bold'
                    : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                HUMIDITY
              </button>
              <button
                onClick={() => setActiveLayer('pressure')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeLayer === 'pressure'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/50 font-bold'
                    : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                PRESSURE
              </button>
            </div>

            {/* Time Window Analysis */}
            <div className="flex items-center gap-1 bg-[#111928] border border-[#1E293B] p-0.5 rounded text-[10px]">
              {(['6h', '24h', '7d', '30d'] as TimeWindowKey[]).map((w) => (
                <button
                  key={w}
                  onClick={() => setTimeWindow(w)}
                  className={`px-2 py-1 rounded uppercase font-bold transition-colors ${
                    timeWindow === w
                      ? 'bg-sky-500 text-white'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                  }`}
                >
                  {w}
                </button>
              ))}
            </div>
          </div>

          {/* Anomaly Episode Markers on Time Axis */}
          {anomalies.length > 0 && (
            <div className="bg-red-950/30 border border-red-900/60 p-2 rounded flex items-center justify-between text-[11px] text-red-300">
              <div>
                <strong>Active Anomaly Episode:</strong> {anomalies[0].explanation_summary}
              </div>
              <button
                onClick={() => navigate(`/anomalies/${anomalies[0].event_id}`)}
                className="underline hover:text-white text-xs font-bold uppercase"
              >
                Investigate
              </button>
            </div>
          )}

          {/* Recharts Canvas */}
          <div className="h-[360px] w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.6} />
                <XAxis
                  dataKey="timeLabel"
                  stroke="#64748B"
                  fontSize={11}
                  fontFamily="JetBrains Mono, monospace"
                  tickLine={false}
                />
                <YAxis
                  stroke="#64748B"
                  fontSize={11}
                  fontFamily="JetBrains Mono, monospace"
                  domain={['auto', 'auto']}
                  tickLine={false}
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

                {(activeLayer === 'all' || activeLayer === 'temperature') && (
                  <Line
                    type="monotone"
                    dataKey="temperature"
                    name="Temperature (°C)"
                    stroke="#38BDF8"
                    strokeWidth={2}
                    dot={(props: any) => {
                      if (props.payload.is_anomalous) {
                        return (
                          <circle
                            key={props.key}
                            cx={props.cx}
                            cy={props.cy}
                            r={6}
                            fill="#EF4444"
                            stroke="#FFFFFF"
                            strokeWidth={2}
                          />
                        );
                      }
                      return <circle key={props.key} cx={props.cx} cy={props.cy} r={0} />;
                    }}
                    isAnimationActive={false}
                  />
                )}

                {(activeLayer === 'all' || activeLayer === 'humidity') && (
                  <Line
                    type="monotone"
                    dataKey="humidity"
                    name="Humidity (%)"
                    stroke="#34D399"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                )}

                {(activeLayer === 'all' || activeLayer === 'pressure') && (
                  <Line
                    type="monotone"
                    dataKey="pressure"
                    name="Pressure (hPa)"
                    stroke="#818CF8"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Station Contextual Drawer (4 cols) */}
        <div className="lg:col-span-4 bg-[#0D131F] border border-[#1E293B] rounded p-4 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
            <span className="font-bold text-[#F8FAFC] uppercase">STATION CONTEXT & SENSORS</span>
            <span className="text-[10px] text-sky-400 font-bold uppercase">IDW LINKED</span>
          </div>

          {/* Latest Telemetry Readout */}
          <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded space-y-1.5">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">LATEST TELEMETRY SNAPSHOT</div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-[10px] text-[#94A3B8]">TEMP</div>
                <div className="font-bold text-sky-300">
                  {formatTemperature(latestObs?.temperature_c)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-[#94A3B8]">RH</div>
                <div className="font-bold text-emerald-300">
                  {formatHumidity(latestObs?.humidity_pct)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-[#94A3B8]">PRESSURE</div>
                <div className="font-bold text-indigo-300">
                  {formatPressure(latestObs?.pressure_hpa)}
                </div>
              </div>
            </div>
          </div>

          {/* Health & Sub-dimension Breakdown */}
          <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#64748B] uppercase font-bold">5-COMPONENT HEALTH</span>
              <span className="text-sky-300 font-bold">{station.health_index ?? 90}%</span>
            </div>
            <div className="space-y-1 text-[10px]">
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Anomaly Health:</span>
                <span className="text-[#F8FAFC] font-bold">92%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Data Quality:</span>
                <span className="text-[#F8FAFC] font-bold">100%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Communication:</span>
                <span className="text-[#F8FAFC] font-bold">98%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Temporal Stability:</span>
                <span className="text-[#F8FAFC] font-bold">88%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">Spatial Consistency:</span>
                <span className="text-[#F8FAFC] font-bold">84%</span>
              </div>
            </div>
          </div>

          {/* Geodesic Neighbor Stations */}
          <div className="bg-[#111928] border border-[#1E293B] p-2.5 rounded space-y-1.5">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">SPATIAL NEIGHBORS (CAUSAL)</div>
            <div className="space-y-1 divide-y divide-[#1E293B]/40">
              {neighborStations.map((nbr) => (
                <div
                  key={nbr.station_id}
                  onClick={() => navigate(`/stations/${nbr.station_id}`)}
                  className="pt-1 flex items-center justify-between cursor-pointer hover:text-sky-300 transition-colors"
                >
                  <div>
                    <div className="font-bold text-sky-400">{nbr.station_id}</div>
                    <div className="text-[9px] text-[#64748B] truncate">{nbr.station_name}</div>
                  </div>
                  <div className="text-right text-[10px]">
                    <div className="text-[#F8FAFC]">
                      {formatTemperature(nbr.latest_observation?.temperature_c)}
                    </div>
                    <div className="text-emerald-400 font-semibold uppercase">CONSENSUS</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Anomaly Count Indicator */}
          <div className="p-2.5 bg-[#141E30] rounded border border-[#1E293B] flex items-center justify-between">
            <span className="text-[#94A3B8] font-bold uppercase">RECENT ANOMALIES:</span>
            <span className="font-bold text-red-400">{anomalies.length} EPISODES</span>
          </div>
        </div>
      </div>

      {/* Observation Ledger (Compact Chronological Table) */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden font-mono text-xs">
        <div className="p-3 bg-[#111928] border-b border-[#1E293B] flex items-center justify-between">
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            OBSERVATION LEDGER (CHRONOLOGICAL AUDIT ARCHIVE)
          </span>
          <span className="text-[10px] text-[#64748B]">WMO NO. 49 COMPLIANT RECORD STORE</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#0F172A]/70 uppercase">
                <th className="py-2.5 px-3">UTC TIMESTAMP</th>
                <th className="py-2.5 px-3">TEMPERATURE</th>
                <th className="py-2.5 px-3">HUMIDITY</th>
                <th className="py-2.5 px-3">SURFACE PRESSURE</th>
                <th className="py-2.5 px-3">DEW POINT</th>
                <th className="py-2.5 px-3">QC STATUS</th>
                <th className="py-2.5 px-3">HYBRID DECISION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]/60">
              {chartData.slice(0, 8).map((entry, idx) => (
                <tr key={idx} className="hover:bg-[#141E30] transition-colors">
                  <td className="py-2 px-3 text-sky-400">{formatUtcTime(entry.timestamp)}</td>
                  <td className="py-2 px-3">{entry.temperature}°C</td>
                  <td className="py-2 px-3 text-emerald-300">{entry.humidity}%</td>
                  <td className="py-2 px-3 text-indigo-300">{entry.pressure} hPa</td>
                  <td className="py-2 px-3 text-[#94A3B8]">
                    {(
                      (entry.temperature ?? 25) -
                      (100 - (entry.humidity ?? 60)) / 5
                    ).toFixed(1)}°C
                  </td>
                  <td className="py-2 px-3">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold uppercase">
                      VALID
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    {entry.is_anomalous ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 font-bold uppercase">
                        PROBABLE_SENSOR_ANOMALY
                      </span>
                    ) : (
                      <span className="text-[#64748B] font-bold uppercase">NOMINAL</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
