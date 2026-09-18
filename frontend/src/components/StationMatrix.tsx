/**
 * SkyGuard AI — Station Matrix Data Grid
 * High-density analytical data grid with multi-column sorting, parameter visibility toggles,
 * search filtering, and direct drilldown to Station Details.
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Station } from '../types/api';
import { formatTemperature, formatHumidity, formatPressure } from '../utils/formatters';

interface StationMatrixProps {
  stations: Station[];
  selectedStationId?: string;
  onSelectStation?: (stationId: string) => void;
}

type SortField =
  | 'station_id'
  | 'station_name'
  | 'status'
  | 'temperature_c'
  | 'humidity_pct'
  | 'pressure_hpa'
  | 'health_index'
  | 'freshness';

export const StationMatrix: React.FC<StationMatrixProps> = ({
  stations,
  selectedStationId,
  onSelectStation,
}) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [sortField, setSortField] = useState<SortField>('status');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  // Parameter column visibility toggles
  const [visibleCols, setVisibleCols] = useState({
    elevation: true,
    temp: true,
    humidity: true,
    pressure: true,
    health: true,
    age: true,
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  // Filter & Sort stations
  const filteredAndSorted = useMemo(() => {
    return stations
      .filter((stn) => {
        // Search Filter
        const query = searchQuery.toLowerCase();
        const matchesQuery =
          stn.station_id.toLowerCase().includes(query) ||
          stn.station_name.toLowerCase().includes(query) ||
          (stn.district && stn.district.toLowerCase().includes(query)) ||
          (stn.state && stn.state.toLowerCase().includes(query));

        if (!matchesQuery) return false;

        // Status Filter
        if (statusFilter === 'ALL') return true;
        if (statusFilter === 'ACTIVE') return stn.status === 'ACTIVE' && !stn.latest_observation?.is_anomalous;
        if (statusFilter === 'ANOMALOUS') return stn.latest_observation?.is_anomalous;
        if (statusFilter === 'DEGRADED') return stn.status === 'DEGRADED';
        if (statusFilter === 'OFFLINE') return stn.status === 'OFFLINE';

        return true;
      })
      .sort((a, b) => {
        let valA: any = a[sortField as keyof Station];
        let valB: any = b[sortField as keyof Station];

        if (sortField === 'temperature_c') {
          valA = a.latest_observation?.temperature_c ?? -999;
          valB = b.latest_observation?.temperature_c ?? -999;
        } else if (sortField === 'humidity_pct') {
          valA = a.latest_observation?.humidity_pct ?? -999;
          valB = b.latest_observation?.humidity_pct ?? -999;
        } else if (sortField === 'pressure_hpa') {
          valA = a.latest_observation?.pressure_hpa ?? -999;
          valB = b.latest_observation?.pressure_hpa ?? -999;
        } else if (sortField === 'freshness') {
          valA = a.latest_observation?.freshness_seconds ?? 9999;
          valB = b.latest_observation?.freshness_seconds ?? 9999;
        } else if (sortField === 'status') {
          const rank: Record<string, number> = {
            CRITICAL: 4,
            ANOMALOUS: 3,
            DEGRADED: 2,
            ACTIVE: 1,
            OFFLINE: 0,
          };
          const statA = a.latest_observation?.is_anomalous ? 'ANOMALOUS' : a.status;
          const statB = b.latest_observation?.is_anomalous ? 'ANOMALOUS' : b.status;
          valA = rank[statA] ?? 0;
          valB = rank[statB] ?? 0;
        }

        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
      });
  }, [stations, searchQuery, statusFilter, sortField, sortAsc]);

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded flex flex-col font-mono text-xs shadow-md">
      {/* Table Header Controls */}
      <div className="p-3.5 bg-[#111928] border-b border-[#1E293B] flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="font-bold text-[#F8FAFC] tracking-wider uppercase text-xs">
            STATION TELEMETRY MATRIX & DENSE STATUS GRID
          </span>
          <div className="text-[11px] text-[#64748B] mt-0.5">
            Displaying {filteredAndSorted.length} of {stations.length} Indian Automatic Weather Stations
          </div>
        </div>

        {/* Filter Controls & Search */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative w-48 sm:w-64">
            <input
              type="text"
              placeholder="Search ID, name, district..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0B0F17] border border-[#1E293B] rounded px-3 py-1 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-sky-500"
            />
          </div>

          <div className="flex items-center gap-1 text-[10px]">
            {['ALL', 'ACTIVE', 'ANOMALOUS', 'DEGRADED', 'OFFLINE'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-2.5 py-1 rounded font-bold transition-colors ${
                  statusFilter === status
                    ? 'bg-sky-600 text-white font-bold'
                    : 'bg-[#141E30] text-[#94A3B8] hover:text-[#F8FAFC] border border-[#1E293B]'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[#1E293B] text-[10px] uppercase font-mono text-[#64748B] bg-[#0F172A]/70">
              <th
                onClick={() => handleSort('station_id')}
                className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
              >
                <span>AWS IDENTIFIER {sortField === 'station_id' ? (sortAsc ? '↑' : '↓') : ''}</span>
              </th>
              <th
                onClick={() => handleSort('station_name')}
                className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
              >
                <span>LOCATION / REGION {sortField === 'station_name' ? (sortAsc ? '↑' : '↓') : ''}</span>
              </th>
              <th
                onClick={() => handleSort('status')}
                className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
              >
                <span>TELEMETRY STATUS {sortField === 'status' ? (sortAsc ? '↑' : '↓') : ''}</span>
              </th>
              {visibleCols.elevation && <th className="py-2.5 px-3">ELEVATION</th>}
              {visibleCols.temp && (
                <th
                  onClick={() => handleSort('temperature_c')}
                  className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
                >
                  <span>TEMP (°C) {sortField === 'temperature_c' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              )}
              {visibleCols.humidity && (
                <th
                  onClick={() => handleSort('humidity_pct')}
                  className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
                >
                  <span>HUMID (%) {sortField === 'humidity_pct' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              )}
              {visibleCols.pressure && (
                <th
                  onClick={() => handleSort('pressure_hpa')}
                  className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
                >
                  <span>PRESS (hPa) {sortField === 'pressure_hpa' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              )}
              {visibleCols.health && (
                <th
                  onClick={() => handleSort('health_index')}
                  className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
                >
                  <span>HEALTH {sortField === 'health_index' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              )}
              {visibleCols.age && (
                <th
                  onClick={() => handleSort('freshness')}
                  className="py-2.5 px-3 cursor-pointer hover:text-[#F8FAFC]"
                >
                  <span>DATA FRESHNESS {sortField === 'freshness' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              )}
              <th className="py-2.5 px-3 text-right">ACTION</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#1E293B]/60 font-mono text-xs">
            {filteredAndSorted.map((stn) => {
              const obs = stn.latest_observation;
              const isSelected = stn.station_id === selectedStationId;
              const isCritical = obs?.anomaly_severity === 'CRITICAL';
              const isAnomalous = obs?.is_anomalous;
              const freshness = obs?.freshness_seconds ?? 15;

              return (
                <tr
                  key={stn.station_id}
                  onClick={() => {
                    onSelectStation?.(stn.station_id);
                  }}
                  className={`hover:bg-[#141E30] transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#142338] border-l-2 border-sky-400'
                      : isCritical
                      ? 'bg-red-950/20'
                      : ''
                  }`}
                >
                  {/* Station Identifier */}
                  <td className="py-2.5 px-3">
                    <div className="font-bold text-sky-400">
                      <span>{stn.station_id}</span>
                    </div>
                  </td>

                  {/* Location / Region */}
                  <td className="py-2.5 px-3">
                    <div className="font-sans font-medium text-[#F8FAFC] truncate max-w-[180px]">
                      {stn.station_name}
                    </div>
                    <div className="text-[10px] text-[#64748B]">
                      {stn.district || stn.state || 'India'}
                    </div>
                  </td>

                  {/* Telemetry Status */}
                  <td className="py-2.5 px-3">
                    {isAnomalous ? (
                      <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-red-950/80 text-red-300 border border-red-800 font-bold uppercase">
                        {obs?.anomaly_decision || 'ANOMALY DETECTED'}
                      </span>
                    ) : stn.status === 'DEGRADED' ? (
                      <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800 font-bold uppercase">
                        DEGRADED
                      </span>
                    ) : stn.status === 'OFFLINE' ? (
                      <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-[#1E293B] text-[#64748B] font-bold uppercase">
                        OFFLINE
                      </span>
                    ) : (
                      <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/60 font-bold uppercase">
                        NOMINAL
                      </span>
                    )}
                  </td>

                  {/* Elevation */}
                  {visibleCols.elevation && (
                    <td className="py-2.5 px-3 text-[#94A3B8]">
                      {stn.elevation_m} m
                    </td>
                  )}

                  {/* Temperature */}
                  {visibleCols.temp && (
                    <td className="py-2.5 px-3">
                      <span
                        className={`font-semibold ${
                          isCritical
                            ? 'text-red-400 bg-red-950/50 px-1 py-0.5 rounded'
                            : 'text-sky-300'
                        }`}
                      >
                        {formatTemperature(obs?.temperature_c)}
                      </span>
                    </td>
                  )}

                  {/* Humidity */}
                  {visibleCols.humidity && (
                    <td className="py-2.5 px-3 text-emerald-300">
                      {formatHumidity(obs?.humidity_pct)}
                    </td>
                  )}

                  {/* Pressure */}
                  {visibleCols.pressure && (
                    <td className="py-2.5 px-3 text-indigo-300">
                      {formatPressure(obs?.pressure_hpa)}
                    </td>
                  )}

                  {/* Health */}
                  {visibleCols.health && (
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-bold ${
                            (stn.health_index || 90) >= 80
                              ? 'text-emerald-400'
                              : (stn.health_index || 90) >= 60
                              ? 'text-amber-400'
                              : 'text-red-400'
                          }`}
                        >
                          {stn.health_index || 90}%
                        </span>
                      </div>
                    </td>
                  )}

                  {/* Freshness */}
                  {visibleCols.age && (
                    <td className="py-2.5 px-3">
                      <span
                        className={`text-[10px] font-semibold ${
                          freshness > 300
                            ? 'text-red-400'
                            : freshness > 60
                            ? 'text-amber-400'
                            : 'text-[#64748B]'
                        }`}
                      >
                        {freshness < 60 ? `${freshness}s ago` : `${Math.round(freshness / 60)}m ago`}
                      </span>
                    </td>
                  )}

                  {/* Actions */}
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/stations/${stn.station_id}`);
                      }}
                      className="text-xs text-sky-400 hover:text-sky-300 font-sans hover:underline font-bold"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
