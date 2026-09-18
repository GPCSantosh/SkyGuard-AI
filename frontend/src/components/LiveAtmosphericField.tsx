/**
 * SkyGuard AI — Live Atmospheric Field Distribution
 * Visual analytical representation of Temperature, Humidity, and Pressure dispersion across AWS nodes.
 */

import React, { useState } from 'react';
import { Station } from '../types/api';

interface LiveAtmosphericFieldProps {
  stations: Station[];
  onSelectStation?: (stationId: string) => void;
}

export const LiveAtmosphericField: React.FC<LiveAtmosphericFieldProps> = ({
  stations,
  onSelectStation,
}) => {
  const [activeParam, setActiveParam] = useState<'temp' | 'humid' | 'press'>('temp');

  // Compute parameter statistics
  const validTemps = stations
    .map((s) => s.latest_observation?.temperature_c)
    .filter((v): v is number => v !== null && v !== undefined);

  const validHumid = stations
    .map((s) => s.latest_observation?.humidity_pct)
    .filter((v): v is number => v !== null && v !== undefined);

  const validPress = stations
    .map((s) => s.latest_observation?.pressure_hpa)
    .filter((v): v is number => v !== null && v !== undefined);

  const getStats = (values: number[]) => {
    if (values.length === 0) return { min: 0, max: 0, avg: 0, median: 0 };
    const sorted = [...values].sort((a, b) => a - b);
    const min = sorted[0];
    const max = sorted[sorted.length - 1];
    const avg = Number((sorted.reduce((a, b) => a + b, 0) / sorted.length).toFixed(1));
    const median = sorted[Math.floor(sorted.length / 2)];
    return { min, max, avg, median };
  };

  const tempStats = getStats(validTemps);
  const humidStats = getStats(validHumid);
  const pressStats = getStats(validPress);

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded p-3.5 space-y-3 font-mono text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#1E293B]">
        <div>
          <h3 className="font-bold uppercase tracking-wider text-[#F8FAFC]">
            Live Atmospheric Field & Spatial Dispersion
          </h3>
        </div>

        {/* Parameter Layer Switcher */}
        <div className="flex items-center gap-1 text-[11px]">
          <button
            onClick={() => setActiveParam('temp')}
            className={`px-2.5 py-1 rounded transition-colors uppercase font-bold ${
              activeParam === 'temp'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/50'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            <span>Temperature (°C)</span>
          </button>
          <button
            onClick={() => setActiveParam('humid')}
            className={`px-2.5 py-1 rounded transition-colors uppercase font-bold ${
              activeParam === 'humid'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            <span>Humidity (%)</span>
          </button>
          <button
            onClick={() => setActiveParam('press')}
            className={`px-2.5 py-1 rounded transition-colors uppercase font-bold ${
              activeParam === 'press'
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/50'
                : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
          >
            <span>Pressure (hPa)</span>
          </button>
        </div>
      </div>

      {/* Dispersion Range Strip and Stats */}
      {activeParam === 'temp' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">NETWORK MIN</div>
              <div className="text-base font-bold text-sky-300">{tempStats.min}°C</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">NETWORK MEAN</div>
              <div className="text-base font-bold text-[#F8FAFC]">{tempStats.avg}°C</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">NETWORK MEDIAN</div>
              <div className="text-base font-bold text-emerald-300">{tempStats.median}°C</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">NETWORK MAX</div>
              <div className="text-base font-bold text-amber-300">{tempStats.max}°C</div>
            </div>
          </div>

          {/* Continuous Distribution Spectrum */}
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-[10px] text-[#64748B]">
              <span>Range: {tempStats.min}°C</span>
              <span>Regional Median ({tempStats.median}°C)</span>
              <span>Range: {tempStats.max}°C</span>
            </div>
            <div className="relative h-7 bg-[#141E30] rounded-sm border border-[#1E293B] flex items-center px-3 overflow-hidden">
              {/* Range gradient line */}
              <div className="absolute inset-x-3 h-1.5 rounded-full bg-gradient-to-r from-sky-500 via-emerald-500 to-amber-500 opacity-40" />

              {/* Station Dots along continuous axis */}
              {stations.map((stn) => {
                const val = stn.latest_observation?.temperature_c;
                if (val === null || val === undefined) return null;
                const span = tempStats.max - tempStats.min || 1;
                const percent = Math.min(
                  96,
                  Math.max(4, ((val - tempStats.min) / span) * 100)
                );
                const isCritical = stn.latest_observation?.anomaly_severity === 'CRITICAL';

                return (
                  <div
                    key={stn.station_id}
                    onClick={() => onSelectStation?.(stn.station_id)}
                    style={{ left: `${percent}%` }}
                    className={`absolute -translate-x-1/2 w-3.5 h-3.5 rounded-full border-2 cursor-pointer transition-transform hover:scale-150 z-10 ${
                      isCritical
                        ? 'bg-red-500 border-white'
                        : 'bg-sky-400 border-[#0D131F] hover:bg-white'
                    }`}
                    title={`${stn.station_id} (${stn.station_name}): ${val}°C`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}

      {activeParam === 'humid' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MIN RH</div>
              <div className="text-base font-bold text-amber-300">{humidStats.min}%</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MEAN RH</div>
              <div className="text-base font-bold text-[#F8FAFC]">{humidStats.avg}%</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MEDIAN RH</div>
              <div className="text-base font-bold text-emerald-300">{humidStats.median}%</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MAX RH</div>
              <div className="text-base font-bold text-sky-300">{humidStats.max}%</div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-[10px] text-[#64748B]">
              <span>Dry ({humidStats.min}%)</span>
              <span>Regional Median ({humidStats.median}%)</span>
              <span>Saturated ({humidStats.max}%)</span>
            </div>
            <div className="relative h-7 bg-[#141E30] rounded-sm border border-[#1E293B] flex items-center px-3 overflow-hidden">
              <div className="absolute inset-x-3 h-1.5 rounded-full bg-gradient-to-r from-amber-500 via-emerald-500 to-sky-500 opacity-40" />
              {stations.map((stn) => {
                const val = stn.latest_observation?.humidity_pct;
                if (val === null || val === undefined) return null;
                const span = humidStats.max - humidStats.min || 1;
                const percent = Math.min(
                  96,
                  Math.max(4, ((val - humidStats.min) / span) * 100)
                );

                return (
                  <div
                    key={stn.station_id}
                    onClick={() => onSelectStation?.(stn.station_id)}
                    style={{ left: `${percent}%` }}
                    className="absolute -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-[#0D131F] hover:bg-white cursor-pointer transition-transform hover:scale-150 z-10"
                    title={`${stn.station_id}: ${val}%`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}

      {activeParam === 'press' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MIN PRESSURE</div>
              <div className="text-base font-bold text-indigo-300">{pressStats.min} hPa</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">NETWORK MEAN</div>
              <div className="text-base font-bold text-[#F8FAFC]">{pressStats.avg} hPa</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">REGIONAL MEDIAN</div>
              <div className="text-base font-bold text-indigo-400">{pressStats.median} hPa</div>
            </div>
            <div className="bg-[#111827] border border-[#1E293B] p-2 rounded">
              <div className="text-[10px] text-[#64748B] uppercase font-bold">MAX PRESSURE</div>
              <div className="text-base font-bold text-sky-300">{pressStats.max} hPa</div>
            </div>
          </div>

          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-[10px] text-[#64748B]">
              <span>Trough ({pressStats.min} hPa)</span>
              <span>Barometric Median ({pressStats.median} hPa)</span>
              <span>Ridge ({pressStats.max} hPa)</span>
            </div>
            <div className="relative h-7 bg-[#141E30] rounded-sm border border-[#1E293B] flex items-center px-3 overflow-hidden">
              <div className="absolute inset-x-3 h-1.5 rounded-full bg-gradient-to-r from-purple-500 via-indigo-500 to-sky-500 opacity-40" />
              {stations.map((stn) => {
                const val = stn.latest_observation?.pressure_hpa;
                if (val === null || val === undefined) return null;
                const span = pressStats.max - pressStats.min || 1;
                const percent = Math.min(
                  96,
                  Math.max(4, ((val - pressStats.min) / span) * 100)
                );

                return (
                  <div
                    key={stn.station_id}
                    onClick={() => onSelectStation?.(stn.station_id)}
                    style={{ left: `${percent}%` }}
                    className="absolute -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-indigo-400 border-2 border-[#0D131F] hover:bg-white cursor-pointer transition-transform hover:scale-150 z-10"
                    title={`${stn.station_id}: ${val} hPa`}
                  />
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
