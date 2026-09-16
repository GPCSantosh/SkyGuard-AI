import React, { useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useStation, useStationHistory, useStationHealth, useStations } from '../hooks/useStations';
import { useAnomalies } from '../hooks/useAnomalies';
import { WeatherTrendChart, TimeSeriesPoint } from '../components/WeatherTrendChart';
import { StationStatus } from '../components/StationStatus';
import { HealthScore } from '../components/HealthScore';
import { HealthTrend } from '../components/HealthTrend';
import { AlertList } from '../components/AlertList';
import { LoadingSkeleton, ErrorState } from '../components/StateFeedback';
import { MapPin, ArrowLeft, Clock, Layers } from 'lucide-react';

export const StationDetailsPage: React.FC = () => {
  const { stationId = 'AWS_001' } = useParams<{ stationId: string }>();
  const navigate = useNavigate();

  const { data: station, isLoading: isLoadingStation, isError } = useStation(stationId);
  const { data: allStations = [] } = useStations();
  const { data: historyData } = useStationHistory(stationId, { limit: 100 });
  const { data: healthData } = useStationHealth(stationId);
  const { data: anomaliesData } = useAnomalies({ stationId, limit: 5 });

  // Map history to 3 time-series datasets
  const { tempData, humData, presData } = useMemo(() => {
    const temp: TimeSeriesPoint[] = [];
    const hum: TimeSeriesPoint[] = [];
    const pres: TimeSeriesPoint[] = [];

    if (historyData?.items) {
      historyData.items.forEach((obs) => {
        temp.push({
          timestamp: obs.timestamp,
          raw: obs.temperature,
          imputed: null,
        });
        hum.push({
          timestamp: obs.timestamp,
          raw: obs.humidity,
          imputed: null,
        });
        pres.push({
          timestamp: obs.timestamp,
          raw: obs.pressure,
          imputed: null,
        });
      });
    }

    return { tempData: temp, humData: hum, presData: pres };
  }, [historyData]);

  // Compute nearest neighbor stations geometrically
  const nearestNeighbors = useMemo(() => {
    if (!station) return [];
    return allStations
      .filter((s) => s.station_id !== stationId)
      .map((s) => {
        const dLat = (s.latitude - station.latitude) * 111;
        const dLon = (s.longitude - station.longitude) * 111 * Math.cos((station.latitude * Math.PI) / 180);
        const dist = Math.sqrt(dLat * dLat + dLon * dLon);
        return { ...s, distanceKm: dist };
      })
      .sort((a, b) => a.distanceKm - b.distanceKm)
      .slice(0, 4);
  }, [station, allStations, stationId]);

  if (isLoadingStation) {
    return <LoadingSkeleton rows={8} height="h-16" />;
  }

  if (isError || !station) {
    return (
      <ErrorState
        title={`Station ${stationId} Not Found`}
        message="Could not load station metadata or telemetry from backend repository."
        onRetry={() => navigate('/network')}
      />
    );
  }

  const latest = station.latest_snapshot;

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="p-3 rounded border border-border bg-surface-1 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/network')}
            className="p-1.5 rounded hover:bg-surface-2 text-slate-400 hover:text-slate-100 transition-colors"
            title="Back to Network Overview"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-h1 font-bold font-mono text-slate-100">{station.station_id}</h1>
              <span className="text-data text-slate-400 font-medium">({station.name})</span>
              <StationStatus status={latest?.status || station.status} />
            </div>
            <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400 mt-0.5">
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3 text-ops-weather" />
                {station.latitude.toFixed(4)}°N, {station.longitude.toFixed(4)}°E ({station.elevation_m}m)
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-slate-500" />
                Interval: {station.sampling_interval_seconds}s
              </span>
            </div>
          </div>
        </div>

        {/* Station switcher quick dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400">Switch Station:</span>
          <select
            value={stationId}
            onChange={(e) => navigate(`/stations/${e.target.value}`)}
            className="bg-surface-2 border border-border text-slate-200 rounded px-2.5 py-1 text-data font-mono focus:outline-none"
          >
            {allStations.map((s) => (
              <option key={s.station_id} value={s.station_id}>
                {s.station_id} — {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 65/35 Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column (65% / 8 cols): 3 Synchronized Recharts */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
            <span>Chronological Telemetry Stream ({historyData?.pagination.total_count ?? 0} observations)</span>
            <span className="text-ops-weather">Cursors synchronized (syncId)</span>
          </div>

          <WeatherTrendChart
            title="Atmospheric Temperature"
            unit="°C"
            data={tempData}
            color="#38BDF8"
            syncId="station-sync"
            height={190}
          />

          <WeatherTrendChart
            title="Relative Humidity"
            unit="%"
            data={humData}
            color="#34D399"
            syncId="station-sync"
            height={190}
          />

          <WeatherTrendChart
            title="Barometric Pressure"
            unit="hPa"
            data={presData}
            color="#818CF8"
            syncId="station-sync"
            height={190}
          />
        </div>

        {/* Right Column (35% / 4 cols): Health, Neighbors, Metadata, Recent Anomalies */}
        <div className="lg:col-span-4 space-y-4">
          {/* Health Summary */}
          <HealthScore
            score={healthData?.overall_health_score ?? latest?.latest_health_score ?? 100}
            band={healthData?.status_band ?? latest?.latest_health_band ?? 'HEALTHY'}
            trend={healthData?.trend ?? 'STABLE'}
            showDisclaimer={true}
          />

          {healthData && (
            <HealthTrend
              components={healthData.components}
              parameterHealth={healthData.parameter_health}
            />
          )}

          {/* Spatial Neighbors */}
          <div className="p-4 rounded border border-border bg-surface-1">
            <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-1.5 mb-2.5">
              <Layers className="w-4 h-4 text-ops-weather" />
              Nearest Topographic Neighbors
            </h3>
            <div className="space-y-1.5">
              {nearestNeighbors.map((nb) => (
                <div
                  key={nb.station_id}
                  onClick={() => navigate(`/stations/${nb.station_id}`)}
                  className="flex items-center justify-between p-2 rounded bg-surface-2 hover:bg-surface-hover cursor-pointer border border-border-subtle text-[11px] font-mono transition-colors"
                >
                  <div>
                    <strong className="text-slate-100">{nb.station_id}</strong>
                    <span className="text-slate-400 ml-1.5">({nb.name})</span>
                  </div>
                  <span className="text-ops-weather font-medium">{nb.distanceKm.toFixed(1)} km</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Anomalies Feed */}
          <div className="space-y-2">
            <h3 className="text-h2 font-semibold text-slate-100">
              Station Anomaly History
            </h3>
            <AlertList anomalies={anomaliesData?.items || []} limit={3} />
          </div>
        </div>
      </div>
    </div>
  );
};
