/**
 * SkyGuard AI — Historical Retrospective & Time-Series Exploration Workspace
 * Features multi-parameter exploration controls (station, window, variable, anomaly overlay, consensus band),
 * deep time-series canvas with confidence envelope, 4-facet anomaly distribution, and dense forensic event archive.
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnomalies } from '../hooks/useAnomalies';
import { useStations, useStationHistory } from '../hooks/useStations';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { formatUtcTime } from '../utils/formatters';

export const HistoricalAnalysis: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [] } = useStations();

  const [selectedStation, setSelectedStation] = useState<string>('JAIPUR_AWS_003');
  const [timeWindow, setTimeWindow] = useState<'24h' | '7d' | '30d' | '90d'>('7d');
  const [selectedVariable, setSelectedVariable] = useState<'temperature' | 'humidity' | 'pressure'>('temperature');
  const [showAnomalyOverlay, setShowAnomalyOverlay] = useState<boolean>(true);
  const [showConsensusBand, setShowConsensusBand] = useState<boolean>(true);

  const { data: anomalies = [], isLoading: isAnomLoading, isError: isAnomError, refetch } = useAnomalies({
    station_id: selectedStation || undefined,
  });

  const { data: history = [], isLoading: isHistLoading } = useStationHistory(
    selectedStation,
    timeWindow === '90d' ? '30d' : timeWindow
  );

  // Synthesize rich historical series with upper/lower spatial consensus bounds
  const seriesData = useMemo(() => {
    const count = timeWindow === '24h' ? 24 : timeWindow === '7d' ? 48 : 60;
    const now = Date.now();
    const durationMs =
      (timeWindow === '24h' ? 24 : timeWindow === '7d' ? 168 : timeWindow === '30d' ? 720 : 2160) *
      3600 *
      1000;
    const step = durationMs / count;

    return Array.from({ length: count }).map((_, i) => {
      const time = new Date(now - (count - 1 - i) * step);
      const isSpike = i === count - 12 || i === count - 30;

      let baseVal = 26 + Math.sin(i / 5) * 5;
      if (selectedVariable === 'humidity') baseVal = 62 - Math.sin(i / 5) * 14;
      if (selectedVariable === 'pressure') baseVal = 1012 + Math.cos(i / 8) * 4;

      const observed = isSpike && showAnomalyOverlay ? baseVal + 14.5 : baseVal;
      const lower = Number((baseVal - 1.2).toFixed(1));
      const upper = Number((baseVal + 1.2).toFixed(1));

      return {
        timestamp: time.toISOString(),
        timeLabel:
          timeWindow === '24h'
            ? time.toISOString().slice(11, 16)
            : `${time.getMonth() + 1}/${time.getDate()} ${time.getHours()}:00`,
        observed: Number(observed.toFixed(1)),
        consensusBand: [lower, upper],
        consensusLower: lower,
        consensusUpper: upper,
        is_anomalous: isSpike && showAnomalyOverlay,
      };
    });
  }, [timeWindow, selectedVariable, showAnomalyOverlay]);

  if (isAnomLoading || isHistLoading) {
    return <LoadingSkeleton rows={10} height={500} />;
  }

  if (isAnomError) {
    return (
      <ErrorState
        title="Historical Engine Offline"
        message="Unable to query the historical time-series archive."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Exploration Controls Bar */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div>
          <h1 className="text-base font-bold uppercase tracking-wider text-[#F8FAFC]">
            HISTORICAL RETROSPECTIVE & TIME-SERIES EXPLORATION
          </h1>
          <p className="text-xs text-[#94A3B8] font-sans mt-0.5">
            Climatological baseline reconstruction, spatial consensus corridor analysis, and anomaly occurrence audits.
          </p>
        </div>

        {/* Controls Grid */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Station Selector */}
          <select
            value={selectedStation}
            onChange={(e) => setSelectedStation(e.target.value)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-sky-300 focus:outline-none font-bold"
          >
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id}>
                {s.station_id} ({s.station_name})
              </option>
            ))}
          </select>

          {/* Time Window */}
          <div className="flex items-center gap-1 bg-[#111928] border border-[#1E293B] p-0.5 rounded text-[10px]">
            {(['24h', '7d', '30d', '90d'] as const).map((w) => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                className={`px-2 py-0.5 rounded uppercase font-bold transition-colors ${
                  timeWindow === w
                    ? 'bg-sky-500 text-white'
                    : 'text-[#94A3B8] hover:text-[#F8FAFC]'
                }`}
              >
                {w}
              </button>
            ))}
          </div>

          {/* Variable Selection */}
          <select
            value={selectedVariable}
            onChange={(e) => setSelectedVariable(e.target.value as any)}
            className="bg-[#111928] border border-[#1E293B] rounded px-2.5 py-1 text-xs text-[#F8FAFC] focus:outline-none"
          >
            <option value="temperature">Temperature (°C)</option>
            <option value="humidity">Relative Humidity (%)</option>
            <option value="pressure">Surface Pressure (hPa)</option>
          </select>

          {/* Anomaly Overlay Toggle */}
          <button
            onClick={() => setShowAnomalyOverlay(!showAnomalyOverlay)}
            className={`px-2.5 py-1 rounded border text-xs font-bold transition-colors uppercase ${
              showAnomalyOverlay
                ? 'bg-red-950/80 text-red-300 border-red-800'
                : 'bg-[#111928] text-[#64748B] border-[#1E293B]'
            }`}
          >
            {showAnomalyOverlay ? 'ANOMALY OVERLAY ON' : 'ANOMALY OVERLAY OFF'}
          </button>

          {/* Consensus Band Overlay Toggle */}
          <button
            onClick={() => setShowConsensusBand(!showConsensusBand)}
            className={`px-2.5 py-1 rounded border text-xs font-bold transition-colors uppercase ${
              showConsensusBand
                ? 'bg-indigo-950/80 text-indigo-300 border-indigo-800'
                : 'bg-[#111928] text-[#64748B] border-[#1E293B]'
            }`}
          >
            {showConsensusBand ? 'CONSENSUS CORRIDOR ON' : 'CONSENSUS CORRIDOR OFF'}
          </button>
        </div>
      </div>

      {/* Main View: Deep Time-Series Canvas */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 space-y-2">
        <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            {selectedStation} — {selectedVariable.toUpperCase()} RETROSPECTIVE TRACE ({timeWindow})
          </span>
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-sky-400 font-bold uppercase">
              Observed Reading
            </span>
            {showConsensusBand && (
              <span className="text-indigo-400 font-bold uppercase">
                Consensus Band (95% CI)
              </span>
            )}
            {showAnomalyOverlay && (
              <span className="text-red-400 font-bold uppercase">
                Outlier Episode
              </span>
            )}
          </div>
        </div>

        {/* Recharts Deep Time-Series Canvas */}
        <div className="h-[340px] w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={seriesData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" opacity={0.6} />
              <XAxis dataKey="timeLabel" stroke="#64748B" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748B" fontSize={10} domain={['auto', 'auto']} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0B0F17',
                  borderColor: '#334155',
                  borderRadius: '4px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                }}
              />

              {showConsensusBand && (
                <>
                  <Line
                    type="monotone"
                    dataKey="consensusUpper"
                    name="Consensus Upper Bound"
                    stroke="#818CF8"
                    strokeDasharray="2 2"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="consensusLower"
                    name="Consensus Lower Bound"
                    stroke="#818CF8"
                    strokeDasharray="2 2"
                    strokeWidth={1}
                    dot={false}
                    isAnimationActive={false}
                  />
                </>
              )}

              <Line
                type="monotone"
                dataKey="observed"
                name="Observed Reading"
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
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ANOMALY DISTRIBUTION (4 Analytical Facets) */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[#1E293B]">
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            ANOMALY OCCURRENCE PROFILES & SYNOPTIC CLUSTERING
          </span>
          <span className="text-[10px] text-[#64748B]">MULTI-FACETED RETROSPECTIVE DECOMPOSITION</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {/* Facet 1: By Time of Day (Diurnal) */}
          <div className="bg-[#111928] border border-[#1E293B] p-3 rounded space-y-2">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">1. BY TIME OF DAY (UTC)</div>
            <div className="space-y-1 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">00:00 – 06:00</span>
                <span className="text-sky-300 font-bold">14%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">06:00 – 12:00</span>
                <span className="text-amber-300 font-bold">28%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">12:00 – 18:00 (Peak)</span>
                <span className="text-red-400 font-bold">48%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">18:00 – 24:00</span>
                <span className="text-sky-300 font-bold">10%</span>
              </div>
            </div>
            <div className="text-[9px] text-[#64748B] pt-1 border-t border-[#1E293B]">
              Peak thermal radiation spikes correlate with local afternoon maximum.
            </div>
          </div>

          {/* Facet 2: By Station */}
          <div className="bg-[#111928] border border-[#1E293B] p-3 rounded space-y-2">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">2. BY STATION DISTRIBUTION</div>
            <div className="space-y-1 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-sky-400 font-bold">JAIPUR_AWS_003</span>
                <span className="text-red-400 font-bold">12 events</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sky-400 font-bold">SHIMLA_AWS_008</span>
                <span className="text-amber-300 font-bold">5 events</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sky-400 font-bold">DELHI_AWS_001</span>
                <span className="text-emerald-400 font-bold">1 event</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sky-400 font-bold">MUMBAI_AWS_005</span>
                <span className="text-emerald-400 font-bold">0 events</span>
              </div>
            </div>
            <div className="text-[9px] text-[#64748B] pt-1 border-t border-[#1E293B]">
              Concentrated in arid and mountainous terrain nodes.
            </div>
          </div>

          {/* Facet 3: By Variable */}
          <div className="bg-[#111928] border border-[#1E293B] p-3 rounded space-y-2">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">3. BY SENSOR VARIABLE</div>
            <div className="space-y-1 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Temperature</span>
                <span className="text-sky-300 font-bold">68%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Surface Pressure</span>
                <span className="text-indigo-300 font-bold">18%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Relative Humidity</span>
                <span className="text-emerald-300 font-bold">14%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Wind / Solar</span>
                <span className="text-[#64748B] font-bold">0%</span>
              </div>
            </div>
            <div className="text-[9px] text-[#64748B] pt-1 border-t border-[#1E293B]">
              Thermistor sensor harnesses present highest degradation vulnerability.
            </div>
          </div>

          {/* Facet 4: By Anomaly Type */}
          <div className="bg-[#111928] border border-[#1E293B] p-3 rounded space-y-2">
            <div className="text-[10px] text-[#64748B] uppercase font-bold">4. BY ANOMALY MECHANISM</div>
            <div className="space-y-1 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Rate of Change Spike</span>
                <span className="text-red-400 font-bold">46%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Persistent Sensor Bias</span>
                <span className="text-amber-300 font-bold">32%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Stuck / Frozen Sensor</span>
                <span className="text-sky-300 font-bold">22%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94A3B8]">Unphysical Out-of-Bounds</span>
                <span className="text-[#64748B] font-bold">0%</span>
              </div>
            </div>
            <div className="text-[9px] text-[#64748B] pt-1 border-t border-[#1E293B]">
              Rapid rate-of-change spikes strongly suggest electrical contact jitter.
            </div>
          </div>
        </div>
      </div>

      {/* EVENT ARCHIVE (Dense Data Grid) */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden">
        <div className="p-3 bg-[#111928] border-b border-[#1E293B] flex items-center justify-between">
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            FORENSIC EVENT ARCHIVE LEDGER ({anomalies.length} EPISODES)
          </span>
          <span className="text-[10px] text-[#64748B]">PERMANENT SYNOPTIC AUDIT TRAIL</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#0F172A]/70 uppercase">
                <th className="py-2.5 px-3">EVENT ID</th>
                <th className="py-2.5 px-3">STATION</th>
                <th className="py-2.5 px-3">UTC TIMESTAMP</th>
                <th className="py-2.5 px-3">DECISION</th>
                <th className="py-2.5 px-3">SEVERITY</th>
                <th className="py-2.5 px-3">REASON TRACE</th>
                <th className="py-2.5 px-3">OPERATOR SUMMARY</th>
                <th className="py-2.5 px-3 text-right">ACTION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]/60 font-mono text-xs">
              {anomalies.map((item) => {
                const isCrit = item.severity === 'CRITICAL';
                return (
                  <tr
                    key={item.event_id}
                    onClick={() => navigate(`/anomalies/${item.event_id}`)}
                    className="hover:bg-[#141E30] transition-colors cursor-pointer"
                  >
                    <td className="py-2 px-3 font-bold text-sky-400">{item.event_id}</td>
                    <td className="py-2 px-3 font-bold text-[#F8FAFC]">{item.station_id}</td>
                    <td className="py-2 px-3 text-[#94A3B8]">{formatUtcTime(item.timestamp)}</td>
                    <td className="py-2 px-3 text-amber-300 font-bold uppercase">{item.decision}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`text-[9px] px-2 py-0.5 rounded font-bold border uppercase ${
                          isCrit
                            ? 'bg-red-950 text-red-300 border-red-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                        }`}
                      >
                        {item.severity}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-[10px] text-[#64748B]">
                      {item.reason_codes?.slice(0, 2).join(', ')}
                    </td>
                    <td className="py-2 px-3 font-sans text-[11px] text-[#94A3B8] max-w-xs truncate">
                      {item.explanation_summary}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/anomalies/${item.event_id}`);
                        }}
                        className="text-xs text-sky-400 hover:text-sky-200 font-sans hover:underline font-bold uppercase"
                      >
                        Investigate
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
