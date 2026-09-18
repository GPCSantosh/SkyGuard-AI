/**
 * SkyGuard AI — Meteorological Weather Trend Chart
 * Recharts time-series with linear interpolation, synchronized cursor (syncId),
 * dual-signal raw (solid) vs imputed (dashed), and missing-value gap preservation.
 */

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
} from 'recharts';
import { WeatherObservation } from '../types/api';

interface WeatherTrendChartProps {
  data: WeatherObservation[];
  parameter: 'temperature_c' | 'humidity_pct' | 'pressure_hpa';
  title: string;
  unit: string;
  syncId?: string;
  height?: number;
  showImputed?: boolean;
  showNeighborMedian?: boolean;
  color?: string;
}

export const WeatherTrendChart: React.FC<WeatherTrendChartProps> = ({
  data,
  parameter,
  title,
  unit,
  syncId = 'skyguard-synced-telemetry',
  height = 180,
  showImputed = true,
  showNeighborMedian = false,
  color,
}) => {
  // Determine parameter semantic color
  const strokeColor =
    color ||
    (parameter === 'temperature_c'
      ? '#38BDF8' // Sky Blue
      : parameter === 'humidity_pct'
      ? '#34D399' // Emerald
      : '#A78BFA'); // Muted Violet

  // Derive imputed key and neighbor key
  const imputedKey =
    parameter === 'temperature_c'
      ? 'imputed_temperature_c'
      : parameter === 'humidity_pct'
      ? 'imputed_humidity_pct'
      : 'imputed_pressure_hpa';

  const neighborKey =
    parameter === 'temperature_c'
      ? 'neighbor_median_temperature_c'
      : parameter === 'humidity_pct'
      ? 'neighbor_median_humidity_pct'
      : 'neighbor_median_pressure_hpa';

  // Format timestamp for X-axis (HH:mm UTC)
  const chartData = data.map((d) => {
    const date = new Date(d.timestamp);
    const timeLabel = !isNaN(date.getTime())
      ? `${String(date.getUTCHours()).padStart(2, '0')}:${String(
          date.getUTCMinutes()
        ).padStart(2, '0')}`
      : d.timestamp;

    return {
      ...d,
      timeLabel,
      rawValue: d[parameter],
      imputedValue: d[imputedKey as keyof WeatherObservation],
      neighborValue: d[neighborKey as keyof WeatherObservation],
    };
  });

  // Calculate dynamic domain
  const validVals = chartData
    .flatMap((d) => [d.rawValue, d.imputedValue])
    .filter((v): v is number => typeof v === 'number' && !isNaN(v));

  let yDomain: [number | string, number | string] = ['auto', 'auto'];
  if (validVals.length > 0) {
    const min = Math.min(...validVals);
    const max = Math.max(...validVals);
    const span = Math.max(1, max - min);
    yDomain = [
      parseFloat((min - span * 0.1).toFixed(1)),
      parseFloat((max + span * 0.1).toFixed(1)),
    ];
  }

  // Find anomaly regions for background bands
  const anomalyPoints = chartData.filter((d) => d.is_anomalous);

  return (
    <div className="w-full bg-[#111827] border border-[#2D3748] rounded p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: strokeColor }}
          />
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#F8FAFC]">
            {title}
          </h4>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-mono text-[#64748B]">
          <span className="flex items-center gap-1.5">
            <span
              className="inline-block w-3 h-0.5"
              style={{ backgroundColor: strokeColor }}
            />
            Raw Sensor
          </span>
          {showImputed && (
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-0.5 border-t border-dashed"
                style={{ borderColor: strokeColor }}
              />
              Imputed
            </span>
          )}
          <span className="text-[#94A3B8] font-bold">[{unit}]</span>
        </div>
      </div>

      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            syncId={syncId}
            margin={{ top: 8, right: 12, left: -20, bottom: 0 }}
          >
            <CartesianGrid stroke="#1F2937" strokeDasharray="3 3" opacity={0.5} />
            <XAxis
              dataKey="timeLabel"
              stroke="#64748B"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono', fill: '#64748B' }}
              tickLine={false}
              axisLine={{ stroke: '#2D3748' }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={yDomain}
              stroke="#64748B"
              tick={{ fontSize: 10, fontFamily: 'JetBrains Mono', fill: '#64748B' }}
              tickLine={false}
              axisLine={{ stroke: '#2D3748' }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) return null;
                const point = payload[0]?.payload as (typeof chartData)[0];
                return (
                  <div className="bg-[#1A2234] border border-[#3D4F6B] p-2.5 rounded shadow-lg text-xs font-mono">
                    <div className="text-[#94A3B8] pb-1 mb-1 border-b border-[#2D3748]">
                      Time: <span className="text-[#F8FAFC]">{label} UTC</span>
                    </div>
                    <div className="flex items-center justify-between gap-4 py-0.5">
                      <span className="text-[#94A3B8]">Raw Sensor:</span>
                      <span className="font-semibold" style={{ color: strokeColor }}>
                        {point.rawValue !== null && point.rawValue !== undefined
                          ? `${point.rawValue} ${unit}`
                          : '—'}
                      </span>
                    </div>
                    {point.imputedValue !== null && point.imputedValue !== undefined && (
                      <div className="flex items-center justify-between gap-4 py-0.5 text-amber-300">
                        <span>Recommended:</span>
                        <span className="font-semibold">
                          {point.imputedValue} {unit}
                        </span>
                      </div>
                    )}
                    {point.is_anomalous && (
                      <div className="mt-1 pt-1 border-t border-[#2D3748] text-[10px] text-red-400 font-bold uppercase">
                        ANOMALY EPISODE DETECTED
                      </div>
                    )}
                  </div>
                );
              }}
            />

            {/* Anomaly Highlight Reference Band */}
            {anomalyPoints.map((ap, i) => (
              <ReferenceArea
                key={i}
                x1={ap.timeLabel}
                x2={ap.timeLabel}
                fill="#EF4444"
                fillOpacity={0.15}
                stroke="#EF4444"
                strokeOpacity={0.4}
              />
            ))}

            {/* Raw Reading Line - Solid, Linear Interpolation */}
            <Line
              type="linear"
              dataKey="rawValue"
              name="Raw Sensor"
              stroke={strokeColor}
              strokeWidth={1.75}
              dot={false}
              activeDot={{ r: 4, fill: strokeColor, stroke: '#111827', strokeWidth: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />

            {/* Imputed/Recommended Line - Dashed */}
            {showImputed && (
              <Line
                type="linear"
                dataKey="imputedValue"
                name="Imputed Estimate"
                stroke={strokeColor}
                strokeWidth={1.5}
                strokeDasharray="4 4"
                strokeOpacity={0.75}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}

            {/* Neighbor Median Line - Dotted */}
            {showNeighborMedian && (
              <Line
                type="linear"
                dataKey="neighborValue"
                name="Neighbor Median"
                stroke="#94A3B8"
                strokeWidth={1}
                strokeDasharray="2 2"
                strokeOpacity={0.6}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
