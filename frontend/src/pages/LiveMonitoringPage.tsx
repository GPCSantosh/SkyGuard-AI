import React, { useState, useMemo } from 'react';
import { useStations } from '../hooks/useStations';
import { useStationHistory } from '../hooks/useStations';
import { MetricTable, ColumnDef } from '../components/MetricTable';
import { StationStatus } from '../components/StationStatus';
import { WeatherTrendChart, TimeSeriesPoint } from '../components/WeatherTrendChart';
import { StationItem } from '../types/api';
import { Search, Filter, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const LiveMonitoringPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [], isLoading } = useStations();
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [healthFilter, setHealthFilter] = useState<string>('ALL');
  const [selectedStationId, setSelectedStationId] = useState<string>('AWS_001');

  // Fetch telemetry for sparkline strip for selected station
  const { data: historyData } = useStationHistory(selectedStationId, { limit: 24 });

  const sparklineData: TimeSeriesPoint[] = useMemo(() => {
    if (!historyData?.items) return [];
    return historyData.items.map((obs) => ({
      timestamp: obs.timestamp,
      raw: obs.temperature,
      imputed: null,
    }));
  }, [historyData]);

  // Filtering
  const filtered = useMemo(() => {
    return stations.filter((s) => {
      const matchSearch =
        s.station_id.toLowerCase().includes(search.toLowerCase()) ||
        s.name.toLowerCase().includes(search.toLowerCase());
      const st = s.latest_snapshot?.status || s.status;
      const matchStatus = statusFilter === 'ALL' || st === statusFilter;
      const score = s.latest_snapshot?.latest_health_score ?? 100;
      let matchHealth = true;
      if (healthFilter === 'DEGRADED') matchHealth = score < 85 && score >= 60;
      if (healthFilter === 'CRITICAL') matchHealth = score < 60;
      if (healthFilter === 'HEALTHY') matchHealth = score >= 85;

      return matchSearch && matchStatus && matchHealth;
    });
  }, [stations, search, statusFilter, healthFilter]);

  // Stations requiring operational attention (degraded/critical or active anomalies)
  const attentionStations = useMemo(() => {
    return stations.filter(
      (s) =>
        (s.latest_snapshot?.latest_health_score ?? 100) < 85 ||
        (s.latest_snapshot?.active_anomaly_count_24h ?? 0) > 0 ||
        (s.latest_snapshot?.status || s.status) !== 'ACTIVE'
    );
  }, [stations]);

  const columns: ColumnDef<StationItem>[] = [
    {
      key: 'station_id',
      header: 'Station Code',
      render: (stn) => (
        <div>
          <span className="font-mono font-bold text-slate-100">{stn.station_id}</span>
          <span className="text-[10px] text-slate-400 block">{stn.name}</span>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'status',
      header: 'Op Status',
      render: (stn) => <StationStatus status={stn.latest_snapshot?.status || stn.status} />,
      sortable: true,
    },
    {
      key: 'temperature',
      header: 'Temperature',
      align: 'right',
      render: (stn) => (
        <span className="font-mono text-ops-weather">
          {stn.latest_snapshot?.latest_temperature_c?.toFixed(1) ?? '--'} °C
        </span>
      ),
      sortable: true,
    },
    {
      key: 'humidity',
      header: 'Relative Humidity',
      align: 'right',
      render: (stn) => (
        <span className="font-mono text-ops-humidity">
          {stn.latest_snapshot?.latest_humidity_pct?.toFixed(0) ?? '--'} %
        </span>
      ),
      sortable: true,
    },
    {
      key: 'pressure',
      header: 'Pressure',
      align: 'right',
      render: (stn) => (
        <span className="font-mono text-ops-pressure">
          {stn.latest_snapshot?.latest_pressure_hpa?.toFixed(1) ?? '--'} hPa
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
      key: 'anomalies_24h',
      header: '24h Flags',
      align: 'center',
      render: (stn) => {
        const c = stn.latest_snapshot?.active_anomaly_count_24h ?? 0;
        return c > 0 ? (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-950 text-red-300 border border-red-800">
            {c}
          </span>
        ) : (
          <span className="text-[11px] font-mono text-slate-500">0</span>
        );
      },
      sortable: true,
    },
    {
      key: 'action',
      header: '',
      align: 'right',
      render: (stn) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/stations/${stn.station_id}`);
          }}
          className="text-[11px] font-mono text-ops-weather hover:underline"
        >
          Details &rarr;
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header & Filter Controls */}
      <div className="p-3 rounded border border-border bg-surface-1 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter station ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 pr-3 py-1 bg-surface-2 border border-border rounded text-data font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-ops-weather"
            />
          </div>

          <div className="flex items-center gap-1.5 text-data">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-surface-2 border border-border text-slate-300 rounded px-2 py-1 text-data font-mono focus:outline-none"
            >
              <option value="ALL">Status: ALL</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="DEGRADED">DEGRADED</option>
              <option value="MAINTENANCE">MAINTENANCE</option>
              <option value="OFFLINE">OFFLINE</option>
            </select>

            <select
              value={healthFilter}
              onChange={(e) => setHealthFilter(e.target.value)}
              className="bg-surface-2 border border-border text-slate-300 rounded px-2 py-1 text-data font-mono focus:outline-none"
            >
              <option value="ALL">Health: ALL</option>
              <option value="HEALTHY">HEALTHY (85+)</option>
              <option value="DEGRADED">DEGRADED (60-84)</option>
              <option value="CRITICAL">CRITICAL (&lt;60)</option>
            </select>
          </div>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          Showing <strong className="text-slate-200">{filtered.length}</strong> of {stations.length} stations
        </div>
      </div>

      {/* Attention & Selected Station Sparkline Strip */}
      {attentionStations.length > 0 && (
        <div className="p-3 rounded border border-amber-900/50 bg-amber-950/20">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-data font-medium text-amber-300">
              <AlertCircle className="w-4 h-4" />
              <span>Stations Requiring Operator Attention ({attentionStations.length})</span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Selected Sparkline: <strong className="text-slate-100">{selectedStationId}</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 pt-1">
            <div className="lg:col-span-1 flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
              {attentionStations.map((stn) => (
                <button
                  key={stn.station_id}
                  onClick={() => setSelectedStationId(stn.station_id)}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition-colors ${
                    selectedStationId === stn.station_id
                      ? 'bg-surface-2 border-ops-weather text-ops-weather font-bold'
                      : 'bg-surface-1 border-border text-slate-300 hover:bg-surface-hover'
                  }`}
                >
                  {stn.station_id} ({Math.round(stn.latest_snapshot?.latest_health_score ?? 100)})
                </button>
              ))}
            </div>

            <div className="lg:col-span-2">
              <WeatherTrendChart
                title={`${selectedStationId} — Recent Temperature Trend`}
                unit="°C"
                data={sparklineData}
                height={120}
              />
            </div>
          </div>
        </div>
      )}

      {/* Main Sortable Station Telemetry Table */}
      <MetricTable
        columns={columns}
        data={filtered}
        isLoading={isLoading}
        selectedRowId={selectedStationId}
        rowIdKey="station_id"
        onRowClick={(row) => setSelectedStationId(row.station_id)}
      />
    </div>
  );
};
