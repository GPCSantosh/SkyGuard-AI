/**
 * SkyGuard AI — Stations Directory & Topology Catalog
 * Overview of all deployed Automatic Weather Stations with geodetic metadata,
 * real-time telemetry indicators, and fast navigation to individual station workspaces.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStations } from '../hooks/useStations';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { formatTemperature, formatHumidity, formatPressure } from '../utils/formatters';

export const StationsCatalog: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [], isLoading, isError, refetch } = useStations();
  const [query, setQuery] = useState('');

  if (isLoading) {
    return <LoadingSkeleton rows={6} height={400} />;
  }

  if (isError) {
    return (
      <ErrorState
        title="Stations Ingest Error"
        message="Unable to load the Automatic Weather Station directory."
        onRetry={() => refetch()}
      />
    );
  }

  const filtered = stations.filter(
    (s) =>
      s.station_id.toLowerCase().includes(query.toLowerCase()) ||
      s.station_name.toLowerCase().includes(query.toLowerCase()) ||
      (s.state && s.state.toLowerCase().includes(query.toLowerCase())) ||
      (s.district && s.district.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Top Banner */}
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold uppercase tracking-wider text-[#F8FAFC]">
            AWS NODE DIRECTORY & TELEMETRY REGISTRY
          </h1>
          <p className="text-xs text-[#94A3B8] font-sans mt-0.5">
            Geographically distributed Automatic Weather Stations across peninsular and northern India.
          </p>
        </div>

        {/* Search */}
        <div className="relative w-72">
          <input
            type="text"
            placeholder="Search station ID, name, state..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#111928] border border-[#1E293B] rounded px-3 py-1.5 text-xs text-[#F8FAFC] placeholder-[#64748B] focus:outline-none focus:border-sky-500"
          />
        </div>
      </div>

      {/* Grid of Station Nodes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.map((station) => {
          const obs = station.latest_observation;
          const isAnomalous = obs?.is_anomalous;
          const isCritical = obs?.anomaly_severity === 'CRITICAL';

          return (
            <div
              key={station.station_id}
              onClick={() => navigate(`/stations/${station.station_id}`)}
              className={`bg-[#0D131F] border rounded p-3.5 hover:border-sky-500 transition-all cursor-pointer flex flex-col justify-between space-y-3 ${
                isCritical
                  ? 'border-red-800/80 bg-red-950/10'
                  : isAnomalous
                  ? 'border-amber-800/80 bg-amber-950/10'
                  : 'border-[#1E293B] hover:bg-[#111928]'
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="font-bold text-sky-400 text-sm">{station.station_id}</div>
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded font-bold border uppercase ${
                      isCritical
                        ? 'bg-red-950 text-red-300 border-red-800'
                        : isAnomalous
                        ? 'bg-amber-950 text-amber-300 border-amber-800'
                        : 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                    }`}
                  >
                    {isAnomalous ? obs?.anomaly_decision || 'ANOMALY' : 'NOMINAL'}
                  </span>
                </div>

                <div className="text-xs text-[#F8FAFC] font-sans font-medium mt-1 truncate">
                  {station.station_name}
                </div>
                <div className="text-[10px] text-[#64748B] mt-0.5">
                  {station.district || 'District'}, {station.state || 'India'}
                </div>
              </div>

              {/* Telemetry Trio */}
              <div className="grid grid-cols-3 gap-1 bg-[#111928] p-2 rounded text-center text-[11px] border border-[#1E293B]">
                <div>
                  <div className="text-[9px] text-[#64748B] uppercase font-bold">TEMP</div>
                  <div className="font-bold text-sky-300">
                    {formatTemperature(obs?.temperature_c)}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-[#64748B] uppercase font-bold">HUMID</div>
                  <div className="font-bold text-emerald-300">
                    {formatHumidity(obs?.humidity_pct)}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] text-[#64748B] uppercase font-bold">PRESS</div>
                  <div className="font-bold text-indigo-300">
                    {formatPressure(obs?.pressure_hpa)}
                  </div>
                </div>
              </div>

              {/* Footer info: Coordinates & Health */}
              <div className="flex items-center justify-between text-[10px] text-[#64748B] pt-1 border-t border-[#1E293B]">
                <span>Health: <strong className="text-sky-300">{station.health_index ?? 90}%</strong></span>
                <span className="text-sky-400 font-bold uppercase hover:underline">
                  Enter Node
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
