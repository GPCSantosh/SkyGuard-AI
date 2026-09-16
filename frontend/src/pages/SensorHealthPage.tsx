import React, { useState } from 'react';
import { useStations, useStationHealth } from '../hooks/useStations';
import { HealthScore } from '../components/HealthScore';
import { HealthTrend } from '../components/HealthTrend';
import { MetricTable, ColumnDef } from '../components/MetricTable';
import { StationItem } from '../types/api';
import { HeartPulse, Wrench } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const SensorHealthPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: stations = [], isLoading: isLoadingStations } = useStations();
  const [selectedStationId, setSelectedStationId] = useState<string>('AWS_001');

  const { data: selectedHealth } = useStationHealth(selectedStationId);

  const activeStation = stations.find((s) => s.station_id === selectedStationId);

  const columns: ColumnDef<StationItem>[] = [
    {
      key: 'station_id',
      header: 'Station ID',
      render: (stn) => (
        <div>
          <span className="font-mono font-bold text-slate-100">{stn.station_id}</span>
          <span className="text-[10px] text-slate-400 block">{stn.name}</span>
        </div>
      ),
      sortable: true,
    },
    {
      key: 'health_score',
      header: 'Health Index',
      align: 'center',
      render: (stn) => {
        const score = stn.latest_snapshot?.latest_health_score ?? 100;
        const color = score < 60 ? 'text-red-400' : score < 85 ? 'text-amber-400' : 'text-emerald-400';
        return <span className={`font-mono font-bold ${color}`}>{Math.round(score)}/100</span>;
      },
      sortable: true,
    },
    {
      key: 'health_band',
      header: 'Status Tier',
      align: 'center',
      render: (stn) => {
        const band = stn.latest_snapshot?.latest_health_band || 'HEALTHY';
        let badgeStyle = 'bg-emerald-950 text-emerald-300 border-emerald-800';
        if (band === 'DEGRADED') badgeStyle = 'bg-amber-950 text-amber-300 border-amber-800';
        if (band === 'CRITICAL') badgeStyle = 'bg-red-950 text-red-300 border-red-800';
        return (
          <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${badgeStyle}`}>
            {band}
          </span>
        );
      },
      sortable: true,
    },
    {
      key: 'anomalies_24h',
      header: '24h Flagged',
      align: 'center',
      render: (stn) => (
        <span className="font-mono text-slate-300">
          {stn.latest_snapshot?.active_anomaly_count_24h ?? 0}
        </span>
      ),
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
            setSelectedStationId(stn.station_id);
          }}
          className={`text-[11px] font-mono px-2 py-0.5 rounded border transition-colors ${
            selectedStationId === stn.station_id
              ? 'bg-ops-weather text-slate-900 border-ops-weather font-bold'
              : 'text-ops-weather border-border hover:bg-surface-hover'
          }`}
        >
          Inspect
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="p-3 rounded border border-border bg-surface-1 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <HeartPulse className="w-5 h-5 text-ops-weather" />
          <div>
            <h1 className="text-h1 font-bold font-mono text-slate-100">
              Sensor Health & Reliability Matrix
            </h1>
            <span className="text-[11px] font-mono text-slate-400">
              Continuous multi-component reliability index (0-100) per Automatic Weather Station
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400">Target Station:</span>
          <select
            value={selectedStationId}
            onChange={(e) => setSelectedStationId(e.target.value)}
            className="bg-surface-2 border border-border text-slate-200 rounded px-2.5 py-1 text-data font-mono focus:outline-none"
          >
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id}>
                {s.station_id} — {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Left Station Diagnostic Panel, Right Network Health Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column (5 cols): Selected Station Health Score & 5 Components */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-3 rounded bg-surface-2 border border-border flex items-center justify-between">
            <span className="font-mono text-data font-semibold text-slate-100">
              {selectedStationId} ({activeStation?.name ?? 'Target Station'})
            </span>
            <button
              onClick={() => navigate(`/stations/${selectedStationId}`)}
              className="text-[11px] font-mono text-ops-weather hover:underline"
            >
              Station Telemetry &rarr;
            </button>
          </div>

          <HealthScore
            score={selectedHealth?.overall_health_score ?? activeStation?.latest_snapshot?.latest_health_score ?? 100}
            band={selectedHealth?.status_band ?? activeStation?.latest_snapshot?.latest_health_band ?? 'HEALTHY'}
            trend={selectedHealth?.trend ?? 'STABLE'}
            showDisclaimer={true}
          />

          <HealthTrend
            components={selectedHealth?.components}
            parameterHealth={selectedHealth?.parameter_health}
          />

          {/* Maintenance Action Recommendation */}
          <div className="p-4 rounded border border-border bg-surface-1">
            <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2 mb-2">
              <Wrench className="w-4 h-4 text-ops-warning" />
              SOP Maintenance Recommendation
            </h3>
            <p className="text-data text-slate-300 bg-surface-2 p-3 rounded border border-border-subtle leading-relaxed">
              {selectedHealth?.maintenance_recommendation ||
                'All subcomponents within nominal calibrated tolerance. Standard scheduled calibration cycle applies.'}
            </p>
          </div>
        </div>

        {/* Right Column (7 cols): Network Health Overview Matrix */}
        <div className="lg:col-span-7 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-h2 font-semibold text-slate-100">
              Network Station Health Rankings
            </h2>
            <span className="text-[11px] font-mono text-slate-400">
              Sorted by operational criticality
            </span>
          </div>

          <MetricTable
            columns={columns}
            data={stations}
            isLoading={isLoadingStations}
            selectedRowId={selectedStationId}
            rowIdKey="station_id"
            onRowClick={(row) => setSelectedStationId(row.station_id)}
          />
        </div>
      </div>
    </div>
  );
};
