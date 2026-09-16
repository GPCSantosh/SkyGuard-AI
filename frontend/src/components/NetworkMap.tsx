import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { StationItem } from '../types/api';
import { useNavigate } from 'react-router-dom';

interface NetworkMapProps {
  stations: StationItem[];
  selectedStationId?: string;
  onSelectStation?: (stationId: string) => void;
  height?: string;
}

// Helper to center map if selectedStation changes
function MapRecenter({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center);
  }, [center, map]);
  return null;
}

// Custom Marker Icon generator
function createStationIcon(status: string, isSelected: boolean) {
  let color = '#10B981'; // Healthy green
  if (status === 'DEGRADED') color = '#F59E0B'; // Amber
  if (status === 'OFFLINE' || status === 'CRITICAL') color = '#EF4444'; // Red

  const border = isSelected ? '3px solid #38BDF8' : '1.5px solid #FFFFFF';
  const size = isSelected ? 18 : 14;

  return L.divIcon({
    className: 'custom-station-pin',
    html: `<div style="
      background-color: ${color};
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      border: ${border};
      box-shadow: 0 0 8px rgba(0,0,0,0.8);
      cursor: pointer;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export const NetworkMap: React.FC<NetworkMapProps> = ({
  stations,
  selectedStationId,
  onSelectStation,
  height = '420px',
}) => {
  const navigate = useNavigate();

  // Compute default center
  const defaultCenter: [number, number] =
    stations.length > 0
      ? [stations[0].latitude, stations[0].longitude]
      : [28.6139, 77.209]; // Default coordinates

  const selectedStation = stations.find((s) => s.station_id === selectedStationId);
  const mapCenter: [number, number] = selectedStation
    ? [selectedStation.latitude, selectedStation.longitude]
    : defaultCenter;

  return (
    <div className="w-full rounded border border-border overflow-hidden relative" style={{ height }}>
      <MapContainer
        center={defaultCenter}
        zoom={6}
        style={{ width: '100%', height: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {selectedStation && <MapRecenter center={mapCenter} />}

        {stations.map((stn) => {
          const isSelected = stn.station_id === selectedStationId;
          const status = stn.latest_snapshot?.status || stn.status;
          const icon = createStationIcon(status, isSelected);

          return (
            <Marker
              key={stn.station_id}
              position={[stn.latitude, stn.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => {
                  if (onSelectStation) {
                    onSelectStation(stn.station_id);
                  }
                },
              }}
            >
              <Popup>
                <div className="text-left font-sans text-xs min-w-[180px]">
                  <div className="flex items-center justify-between border-b border-border-subtle pb-1 mb-1.5">
                    <strong className="font-mono text-slate-100">{stn.name}</strong>
                    <span className="text-[10px] font-mono text-slate-400">[{stn.station_id}]</span>
                  </div>
                  <div className="space-y-0.5 text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Status:</span>
                      <span className="font-mono font-medium">{status}</span>
                    </div>
                    {stn.latest_snapshot?.latest_temperature_c !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Temp:</span>
                        <span className="font-mono font-medium text-ops-weather">
                          {stn.latest_snapshot.latest_temperature_c?.toFixed(1)} °C
                        </span>
                      </div>
                    )}
                    {stn.latest_snapshot?.latest_humidity_pct !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Humidity:</span>
                        <span className="font-mono font-medium text-ops-humidity">
                          {stn.latest_snapshot.latest_humidity_pct?.toFixed(1)} %
                        </span>
                      </div>
                    )}
                    {stn.latest_snapshot?.latest_health_score !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">Health:</span>
                        <span className="font-mono font-medium text-emerald-400">
                          {Math.round(stn.latest_snapshot.latest_health_score ?? 100)}/100
                        </span>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => navigate(`/stations/${stn.station_id}`)}
                    className="w-full mt-2 py-1 px-2 rounded bg-surface-2 hover:bg-surface-hover text-ops-weather border border-border-subtle text-[11px] font-mono text-center font-medium transition-colors"
                  >
                    View Station Details &rarr;
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
};
