/**
 * SkyGuard AI — Interactive Leaflet GIS Network Map
 * Renders Indian AWS topology with severity markers, status pins, and topological neighbor links.
 */

import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
} from 'react-leaflet';
import L from 'leaflet';
import { Station } from '../types/api';
import { formatTemperature, formatHumidity, formatPressure } from '../utils/formatters';

interface NetworkMapProps {
  stations: Station[];
  selectedStationId?: string;
  neighborLinks?: Array<{ from: [number, number]; to: [number, number]; label?: string }>;
  height?: string | number;
  center?: [number, number];
  zoom?: number;
  interactive?: boolean;
}

// Custom Leaflet DivIcon generator
function createStationIcon(
  status: string,
  isSelected: boolean,
  hasCriticalAnomaly: boolean
) {
  let color = '#10B981'; // Green
  let size = 12;

  if (hasCriticalAnomaly || status === 'CRITICAL') {
    color = '#EF4444'; // Red
    size = 18;
  } else if (status === 'DEGRADED' || status === 'WARNING' || status === 'ATTENTION') {
    color = '#F59E0B'; // Amber
    size = 14;
  } else if (status === 'OFFLINE') {
    color = '#64748B'; // Slate
    size = 10;
  }

  if (isSelected) {
    size += 4;
  }

  const border = isSelected ? '2px solid #38BDF8' : '1.5px solid #0B0F17';

  return L.divIcon({
    className: 'custom-station-pin',
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${color};
        border-radius: 50%;
        border: ${border};
        box-shadow: 0 0 ${isSelected ? '10px #38BDF8' : '4px rgba(0,0,0,0.8)'};
        transition: transform 0.2s ease;
      "></div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

export const NetworkMap: React.FC<NetworkMapProps> = ({
  stations,
  selectedStationId,
  neighborLinks = [],
  height = '100%',
  center = [28.6139, 77.209], // New Delhi / Northern India center
  zoom = 9,
}) => {
  const navigate = useNavigate();

  // Selected station coordinates
  const selectedStation = useMemo(
    () => stations.find((s) => s.station_id === selectedStationId),
    [stations, selectedStationId]
  );

  // Dynamic links between selected station and all other stations if none provided
  const activeLinks = useMemo(() => {
    if (neighborLinks.length > 0) return neighborLinks;
    if (selectedStation) {
      return stations
        .filter((s) => s.station_id !== selectedStation.station_id)
        .slice(0, 3)
        .map((nbr) => ({
          from: [selectedStation.latitude, selectedStation.longitude] as [number, number],
          to: [nbr.latitude, nbr.longitude] as [number, number],
          label: `${nbr.station_id}`,
        }));
    }
    return [];
  }, [neighborLinks, selectedStation, stations]);

  return (
    <div
      className="relative w-full border border-[#2D3748] rounded overflow-hidden bg-[#0B0F17]"
      style={{ height }}
    >
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
        attributionControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={18}
        />

        {/* Topological Neighbor Links */}
        {activeLinks.map((link, idx) => (
          <Polyline
            key={idx}
            positions={[link.from, link.to]}
            pathOptions={{
              color: '#38BDF8',
              weight: 1.5,
              dashArray: '4 4',
              opacity: 0.7,
            }}
          />
        ))}

        {/* AWS Station Markers */}
        {stations.map((stn) => {
          const isSelected = stn.station_id === selectedStationId;
          const isCritical =
            stn.latest_observation?.anomaly_severity === 'CRITICAL';

          const icon = createStationIcon(stn.status, isSelected, isCritical);
          const obs = stn.latest_observation;

          return (
            <Marker
              key={stn.station_id}
              position={[stn.latitude, stn.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => {
                  navigate(`/stations/${stn.station_id}`);
                },
              }}
            >
              <Popup>
                <div className="font-mono text-xs">
                  <div className="font-bold text-[#F8FAFC] flex items-center justify-between gap-2 border-b border-[#2D3748] pb-1 mb-1.5">
                    <span>{stn.station_id}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded ${
                        stn.status === 'ACTIVE'
                          ? 'bg-emerald-950 text-emerald-300'
                          : 'bg-amber-950 text-amber-300'
                      }`}
                    >
                      {stn.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-[#94A3B8] font-sans font-medium mb-1.5">
                    {stn.station_name}
                  </div>
                  <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-[#94A3B8]">
                    <span>Temp:</span>
                    <span className="text-sky-300 font-bold">
                      {formatTemperature(obs?.temperature_c)}
                    </span>
                    <span>Humidity:</span>
                    <span className="text-emerald-300">
                      {formatHumidity(obs?.humidity_pct)}
                    </span>
                    <span>Pressure:</span>
                    <span className="text-indigo-300">
                      {formatPressure(obs?.pressure_hpa)}
                    </span>
                    <span>Health:</span>
                    <span className="text-[#F8FAFC] font-bold">
                      {stn.health_index || 90}/100
                    </span>
                  </div>
                  <div className="mt-2 pt-1 border-t border-[#2D3748] text-right">
                    <button
                      onClick={() => navigate(`/stations/${stn.station_id}`)}
                      className="text-[10px] text-sky-400 hover:text-sky-300 font-mono underline"
                    >
                      Inspect Profile →
                    </button>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-2 left-2 z-[400] bg-[#111827]/90 border border-[#2D3748] rounded px-2.5 py-1.5 text-[10px] font-mono text-[#94A3B8] flex items-center gap-3 shadow-md pointer-events-none">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
          Normal
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
          Warning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
          Critical Anomaly
        </span>
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" />
          Offline
        </span>
      </div>
    </div>
  );
};
