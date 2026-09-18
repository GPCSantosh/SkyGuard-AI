/**
 * SkyGuard AI — Anomaly Spatial Context Map
 * Compact interactive map illustrating target station with neighbor stations and geodesic connection lines.
 */

import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';

interface NeighborData {
  station_id: string;
  station_name: string;
  distance_km: number;
  temperature_c: number;
  lat: number;
  lon: number;
}

interface AnomalySpatialContextProps {
  targetStationId: string;
  targetLat: number;
  targetLon: number;
  targetValue: number;
  neighbors: NeighborData[];
}

export const AnomalySpatialContext: React.FC<AnomalySpatialContextProps> = ({
  targetStationId,
  targetLat,
  targetLon,
  targetValue,
  neighbors,
}) => {
  const targetIcon = L.divIcon({
    className: 'target-station-pin',
    html: `
      <div style="
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #EF4444;
        border: 2px solid #FFFFFF;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.8);
      "></div>
    `,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

  const neighborIcon = L.divIcon({
    className: 'neighbor-station-pin',
    html: `
      <div style="
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #10B981;
        border: 1.5px solid #FFFFFF;
      "></div>
    `,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

  const center: [number, number] = [targetLat || 28.58, targetLon || 77.2];

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden flex flex-col h-[320px] font-mono text-xs">
      <div className="p-2.5 bg-[#111928] border-b border-[#1E293B] flex items-center justify-between">
        <div>
          <span className="font-bold text-[#F8FAFC] uppercase tracking-wider">
            SPATIAL NEIGHBOR TOPOLOGY & ISOLATION MESH
          </span>
        </div>
        <span className="text-[10px] text-red-400 font-bold uppercase">
          3/3 NEIGHBORS DISAGREE
        </span>
      </div>

      <div className="flex-1 relative">
        <MapContainer
          center={center}
          zoom={8}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />

          {/* Target Station Marker */}
          <Marker position={[targetLat, targetLon]} icon={targetIcon}>
            <Popup className="dark-popup">
              <div className="text-xs font-mono p-1">
                <strong className="text-red-400">{targetStationId} (Target)</strong>
                <div>Value: {targetValue}°C</div>
                <div className="text-amber-400">Isolated anomaly</div>
              </div>
            </Popup>
          </Marker>

          {/* Neighbor Station Markers & Vectors */}
          {neighbors.map((nbr) => (
            <React.Fragment key={nbr.station_id}>
              <Polyline
                positions={[
                  [targetLat, targetLon],
                  [nbr.lat, nbr.lon],
                ]}
                color="#64748B"
                dashArray="4, 6"
                weight={1.5}
                opacity={0.7}
              />
              <Marker position={[nbr.lat, nbr.lon]} icon={neighborIcon}>
                <Popup className="dark-popup">
                  <div className="text-xs font-mono p-1">
                    <strong className="text-emerald-400">{nbr.station_id}</strong>
                    <div>{nbr.station_name}</div>
                    <div>Value: {nbr.temperature_c}°C</div>
                    <div>Distance: {nbr.distance_km} km</div>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          ))}
        </MapContainer>
      </div>

      {/* Neighbor list summary below */}
      <div className="p-2 bg-[#0A0E17] border-t border-[#1E293B] flex items-center justify-between text-[10px] text-[#94A3B8] overflow-x-auto gap-3">
        {neighbors.map((nbr) => (
          <div key={nbr.station_id} className="whitespace-nowrap">
            <span className="text-emerald-400 font-bold">{nbr.station_id}:</span>{' '}
            {nbr.temperature_c}°C ({nbr.distance_km}km)
          </div>
        ))}
      </div>
    </div>
  );
};
