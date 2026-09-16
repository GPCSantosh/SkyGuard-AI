import React from 'react';
import { NeighborContextRecord } from '../types/api';
import { Check, X } from 'lucide-react';

interface NeighborComparisonProps {
  neighbors: NeighborContextRecord[];
  targetStationId?: string;
  targetValue?: number | null;
  unit?: string;
}

export const NeighborComparison: React.FC<NeighborComparisonProps> = ({
  neighbors,
  targetStationId,
  targetValue,
  unit = '°C',
}) => {
  return (
    <div className="p-4 rounded border border-border bg-surface-1">
      <div className="flex items-center justify-between mb-3 border-b border-border-subtle pb-2">
        <h3 className="text-h2 font-semibold text-slate-100">
          Spatial Neighborhood Cross-Validation
        </h3>
        {targetStationId && (
          <span className="text-[11px] font-mono text-slate-400">
            Target [{targetStationId}]:{' '}
            <strong className="text-slate-100 font-mono">
              {typeof targetValue === 'number' ? `${targetValue.toFixed(1)} ${unit}` : '--'}
            </strong>
          </span>
        )}
      </div>

      {neighbors.length === 0 ? (
        <span className="text-data text-slate-400 italic">
          No contemporaneous spatial neighbors within radius.
        </span>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse table-dense">
            <thead>
              <tr className="bg-surface-2/60 border-b border-border">
                <th className="text-[11px] font-mono text-slate-400 uppercase">Neighbor Station</th>
                <th className="text-[11px] font-mono text-slate-400 uppercase text-right">Distance (km)</th>
                <th className="text-[11px] font-mono text-slate-400 uppercase text-right">Observed ({unit})</th>
                <th className="text-[11px] font-mono text-slate-400 uppercase text-right">Delta ({unit})</th>
                <th className="text-[11px] font-mono text-slate-400 uppercase text-center">Consistency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {neighbors.map((nb) => (
                <tr key={nb.neighbor_station_id} className="hover:bg-surface-2/40">
                  <td className="font-mono text-slate-200">{nb.neighbor_station_id}</td>
                  <td className="text-right font-mono text-slate-400">{nb.distance_km.toFixed(1)} km</td>
                  <td className="text-right font-mono text-slate-200">
                    {typeof nb.observed_value === 'number' ? nb.observed_value.toFixed(1) : '--'}
                  </td>
                  <td className="text-right font-mono text-slate-300">
                    {typeof nb.delta === 'number'
                      ? `${nb.delta > 0 ? '+' : ''}${nb.delta.toFixed(1)}`
                      : '--'}
                  </td>
                  <td className="text-center">
                    {nb.is_consistent ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800">
                        <Check className="w-3 h-3" /> Corroborated
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-red-400 bg-red-950/60 px-1.5 py-0.5 rounded border border-red-800">
                        <X className="w-3 h-3" /> Discordant
                      </span>
                    )}
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
