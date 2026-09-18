import React from 'react';

export interface NeighborItem {
  station_id: string;
  station_name?: string;
  distance_km: number;
  temperature_c?: number | null;
  humidity_pct?: number | null;
  pressure_hpa?: number | null;
  status: 'AGREE' | 'DISAGREE' | 'UNKNOWN';
}

interface NeighborComparisonProps {
  neighbors: NeighborItem[];
  targetStationId: string;
  targetValue?: number;
  variableName?: string;
}

export const NeighborComparison: React.FC<NeighborComparisonProps> = ({
  neighbors,
  targetStationId,
  targetValue,
  variableName = 'Temperature',
}) => {
  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden">
      <div className="p-3 bg-[#111827] border-b border-[#1E293B] flex items-center justify-between">
        <h3 className="font-mono text-xs font-bold text-[#F8FAFC] uppercase tracking-wider">
          Spatial Consensus Verification (IDW Neighbors)
        </h3>
        <span className="font-mono text-[11px] text-[#64748B]">
          Geodesic Proximity Mesh
        </span>
      </div>

      <div className="p-3 bg-[#0A0E17] border-b border-[#1E293B] flex flex-wrap items-center justify-between text-xs font-mono gap-2">
        <div>
          <span className="text-[#64748B]">TARGET NODE:</span>{' '}
          <strong className="text-[#F8FAFC]">{targetStationId}</strong>
        </div>
        <div>
          <span className="text-[#64748B]">TARGET OBSERVATION:</span>{' '}
          <strong className="text-red-400">
            {targetValue !== undefined ? `${targetValue} °C` : '—'}
          </strong>
        </div>
        <div>
          <span className="text-[#64748B]">PARAMETER:</span>{' '}
          <span className="text-[#38BDF8]">{variableName}</span>
        </div>
      </div>

      {neighbors.length === 0 ? (
        <div className="p-4 text-center font-mono text-xs text-[#64748B]">
          No adjacent sensor stations within active IDW radius.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#111827] uppercase">
                <th className="py-2 px-2.5">Station ID</th>
                <th className="py-2 px-2.5">Distance</th>
                <th className="py-2 px-2.5">Observed</th>
                <th className="py-2 px-2.5 text-right">Consensus</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E293B]/60">
              {neighbors.map((nbr) => (
                <tr key={nbr.station_id} className="hover:bg-[#111827] transition-colors">
                  <td className="py-2 px-2.5 font-semibold text-[#F8FAFC]">
                    {nbr.station_id}
                  </td>
                  <td className="py-2 px-2.5 text-[#94A3B8]">
                    {nbr.distance_km} km
                  </td>
                  <td className="py-2 px-2.5 text-[#38BDF8] font-semibold">
                    {nbr.temperature_c !== undefined && nbr.temperature_c !== null
                      ? `${nbr.temperature_c} °C`
                      : nbr.pressure_hpa !== undefined && nbr.pressure_hpa !== null
                      ? `${nbr.pressure_hpa} hPa`
                      : '—'}
                  </td>
                  <td className="py-2 px-2.5 text-right">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border font-bold uppercase ${
                        nbr.status === 'AGREE'
                          ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60'
                          : 'bg-red-950/40 text-red-300 border-red-800/60'
                      }`}
                    >
                      {nbr.status === 'AGREE' ? 'AGREE' : 'DISAGREE'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
