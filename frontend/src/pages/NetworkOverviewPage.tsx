import React, { useState } from 'react';
import { useStations } from '../hooks/useStations';
import { useAnomalies } from '../hooks/useAnomalies';
import { useSystemHealth } from '../hooks/useSystem';
import { NetworkMap } from '../components/NetworkMap';
import { AlertList } from '../components/AlertList';
import { MetricTable, ColumnDef } from '../components/MetricTable';
import { StationStatus } from '../components/StationStatus';
import { StationItem } from '../types/api';
import { useNavigate } from 'react-router-dom';
import { Radio, Activity, AlertTriangle, ShieldCheck, Search } from 'lucide-react';

export const NetworkOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [], isLoading: isLoadingStations } = useStations();
  const { data: anomalyData, isLoading: isLoadingAnomalies } = useAnomalies({ limit: 10 });
  const { data: systemHealth } = useSystemHealth();
  const [searchQuery, setSearchQuery] = useState<string>('');

  const activeAnomalies = anomalyData?.items || [];
  const totalStations = stations.length;
  const activeStations = stations.filter(
    (s) => (s.latest_snapshot?.status || s.status) === 'ACTIVE'
  ).length;

  const meanHealth =
    stations.length > 0
      ? Math.round(
          stations.reduce(
            (acc, s) => acc + (s.latest_snapshot?.latest_health_score ?? 100),
            0
          ) / stations.length
        )
      : 100;

  // Filtered station list for table
  const filteredStations = stations.filter(
    (s) =>
      s.station_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.state && s.state.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const columns: ColumnDef<StationItem>[] = [
    {
      key: 'station_id',
      header: 'Station ID',
      render: (stn) => (
        <div>
          <span className="font-mono font-semibold text-slate-100">{stn.station_id}</span>
          <span className="text-[10px] text-slate-400 block truncate">{stn.name}</span>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'status',
      header: 'Status',
      render: (stn) => <StationStatus status={stn.latest_snapshot?.status || stn.status} />,
      sortable: true,
    },
    {
      key: 'temperature',
      header: 'Temp (°C)',
      align: 'right',
      render: (stn) => (
        <span className="text-ops-weather font-mono">
          {stn.latest_snapshot?.latest_temperature_c !== undefined &&
          stn.latest_snapshot?.latest_temperature_c !== null
            ? `${stn.latest_snapshot.latest_temperature_c.toFixed(1)}°`
            : '--'}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'humidity',
      header: 'Humidity (%)',
      align: 'right',
      render: (stn) => (
        <span className="text-ops-humidity font-mono">
          {stn.latest_snapshot?.latest_humidity_pct !== undefined &&
          stn.latest_snapshot?.latest_humidity_pct !== null
            ? `${stn.latest_snapshot.latest_humidity_pct.toFixed(0)}%`
            : '--'}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'pressure',
      header: 'Pressure (hPa)',
      align: 'right',
      render: (stn) => (
        <span className="text-ops-pressure font-mono">
          {stn.latest_snapshot?.latest_pressure_hpa !== undefined &&
          stn.latest_snapshot?.latest_pressure_hpa !== null
            ? `${stn.latest_snapshot.latest_pressure_hpa.toFixed(1)}`
            : '--'}
        </span>
      ),
      sortable: true,
    },
    {
      key: 'health',
      header: 'Health Index',
      align: 'center',
      render: (stn) => {
        const score = stn.latest_snapshot?.latest_health_score ?? 100;
        const color = score < 60 ? 'text-red-400' : score < 85 ? 'text-amber-400' : 'text-emerald-400';
        return <span className={`font-mono font-medium ${color}`}>{Math.round(score)}/100</span>;
      },
      sortable: true,
    },
    {
      key: 'last_seen',
      header: 'Last Seen (UTC)',
      align: 'right',
      render: (stn) => (
        <span className="text-[11px] font-mono text-slate-400">
          {stn.latest_snapshot?.last_seen_timestamp
            ? new Date(stn.latest_snapshot.last_seen_timestamp).toISOString().substring(11, 19) + 'Z'
            : '--'}
        </span>
      ),
    },
    {
      key: 'anomalies',
      header: 'Active 24h',
      align: 'center',
      render: (stn) => {
        const count = stn.latest_snapshot?.active_anomaly_count_24h ?? 0;
        return count > 0 ? (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-950 text-red-300 border border-red-800">
            {count} FLAG
          </span>
        ) : (
          <span className="text-[11px] font-mono text-slate-500">0</span>
        );
      },
      sortable: true,
    },
  ];

  return (
    <div className="space-y-4">
      {/* 1. Compact Network Operational Status Strip */}
      <div className="p-3 rounded border border-border bg-surface-1 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-ops-weather" />
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Active Stations</span>
              <span className="text-h2 font-mono font-bold text-slate-100">
                {activeStations} <span className="text-slate-500 text-data font-normal">/ {totalStations}</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-ops-warning" />
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Active Anomalies</span>
              <span className="text-h2 font-mono font-bold text-slate-100">
                {activeAnomalies.length}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Network Health</span>
              <span className="text-h2 font-mono font-bold text-emerald-400">
                {meanHealth}/100
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-ops-pressure" />
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase block">Pipeline Latency</span>
              <span className="text-h2 font-mono font-bold text-slate-100">
                {systemHealth?.mean_pipeline_latency_ms ?? 5.8} ms
              </span>
            </div>
          </div>
        </div>

        <div className="text-right text-[11px] font-mono text-slate-400 hidden sm:block">
          <div>Topology Nodes: <strong className="text-slate-200">{totalStations}</strong></div>
          <div>Sampling Cadence: <strong className="text-slate-200">5 min</strong></div>
        </div>
      </div>

      {/* 2. Middle Row: Spatial Map + Active Alert Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
              Automatic Weather Station Topology
            </h2>
            <span className="text-[11px] font-mono text-slate-400">
              Interactive Leaflet GIS Layer
            </span>
          </div>
          <NetworkMap
            stations={stations}
            height="380px"
            onSelectStation={(id) => navigate(`/stations/${id}`)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-h2 font-semibold text-slate-100">
              Active Anomaly Stream
            </h2>
            <button
              onClick={() => navigate('/anomalies')}
              className="text-[11px] font-mono text-ops-weather hover:underline"
            >
              View all &rarr;
            </button>
          </div>
          <AlertList anomalies={activeAnomalies} isLoading={isLoadingAnomalies} limit={5} />
        </div>
      </div>

      {/* 3. Bottom Row: High-Density Station Telemetry Table */}
      <div className="space-y-2 pt-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-h2 font-semibold text-slate-100">
            Network Telemetry Matrix
          </h2>
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search station ID or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1 bg-surface-2 border border-border rounded text-data font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-ops-weather"
            />
          </div>
        </div>

        <MetricTable
          columns={columns}
          data={filteredStations}
          isLoading={isLoadingStations}
          rowIdKey="station_id"
          onRowClick={(row) => navigate(`/stations/${row.station_id}`)}
          emptyMessage="No weather stations matched the search query."
        />
      </div>
    </div>
  );
};
