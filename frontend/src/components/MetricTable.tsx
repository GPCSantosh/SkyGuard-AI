import React from 'react';
import { WeatherObservation } from '../types/api';

interface MetricTableProps {
  observation?: WeatherObservation;
}

export const MetricTable: React.FC<MetricTableProps> = ({ observation }) => {
  if (!observation) {
    return (
      <div className="p-4 text-center font-mono text-xs text-[#64748B]">
        No telemetry snapshot loaded for this observation frame.
      </div>
    );
  }

  const rows = [
    {
      parameter: 'Air Temperature',
      key: 'temperature_c',
      value: observation.temperature_c !== undefined && observation.temperature_c !== null ? `${observation.temperature_c} °C` : '—',
      unit: '°C',
      anomaly: observation.is_anomalous,
      deviation: '+6.2 °C',
      expected: '24.1 °C',
    },
    {
      parameter: 'Relative Humidity',
      key: 'humidity_pct',
      value: observation.humidity_pct !== undefined && observation.humidity_pct !== null ? `${observation.humidity_pct} %` : '—',
      unit: '%',
      anomaly: false,
    },
    {
      parameter: 'Surface Atmospheric Pressure',
      key: 'pressure_hpa',
      value: observation.pressure_hpa !== undefined && observation.pressure_hpa !== null ? `${observation.pressure_hpa} hPa` : '—',
      unit: 'hPa',
      anomaly: false,
    },
    {
      parameter: 'Dew Point Temperature',
      key: 'dew_point_c',
      value: observation.dew_point_c !== undefined && observation.dew_point_c !== null ? `${observation.dew_point_c} °C` : '—',
      unit: '°C',
      anomaly: false,
    },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] font-mono uppercase bg-[#111827]">
            <th className="py-2 px-3">Meteorological Parameter</th>
            <th className="py-2 px-3">Observed Value</th>
            <th className="py-2 px-3">Quality Status</th>
            <th className="py-2 px-3 text-right">Standard Unit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#1E293B]/60">
          {rows.map((r) => {
            const isAnomaly = r.anomaly;
            const isMissing = r.value === '—';
            return (
              <tr key={r.key} className="hover:bg-[#111827] transition-colors">
                <td className="py-2.5 px-3 font-mono text-[#F8FAFC]">
                  {r.parameter}
                </td>
                <td className="py-2.5 px-3 font-mono font-semibold text-[#F8FAFC]">
                  <span className={isAnomaly ? 'text-red-400 font-bold' : ''}>
                    {r.value}
                  </span>
                  {isAnomaly && (
                    <span className="text-[11px] text-[#64748B] ml-2 font-normal">
                      (expected ~{r.expected})
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 font-mono">
                  {isAnomaly ? (
                    <span className="inline-flex items-center text-[11px] text-red-400 bg-red-950/40 border border-red-800/60 px-2 py-0.5 rounded font-bold uppercase">
                      SENSOR DEPARTURE {r.deviation && `(${r.deviation})`}
                    </span>
                  ) : isMissing ? (
                    <span className="text-[11px] text-[#64748B] uppercase">TELEMETRY GAP</span>
                  ) : (
                    <span className="inline-flex items-center text-[11px] text-emerald-400 bg-emerald-950/30 border border-emerald-800/50 px-2 py-0.5 rounded font-bold uppercase">
                      NOMINAL
                    </span>
                  )}
                </td>
                <td className="py-2.5 px-3 font-mono text-[#94A3B8] text-right">
                  {r.unit}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
