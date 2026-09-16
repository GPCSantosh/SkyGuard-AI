import React from 'react';
import { NeighborContextRecord } from '../types/api';
import { formatDistance, formatTemperature } from '../utils/formatters';
import { Check, X, MapPin } from 'lucide-react';

interface NeighborComparisonProps {
  neighbors: NeighborContextRecord[];
  targetStationId?: string;
  targetValue?: number | null;
  unit?: string;
  targetVariable?: string;
}

export const NeighborComparison: React.FC<NeighborComparisonProps> = ({
  neighbors = [],
  targetStationId,
  targetValue,
  unit = '°C',
  targetVariable = 'Temperature',
}) => {
  const agreeingCount = neighbors.filter((n) => n.is_consistent).length;
  const totalCount = neighbors.length;
  const isIsolated = totalCount > 0 && agreeingCount === 0;

  return (
    <div className="p-4 rounded border border-border bg-surface-1 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2.5">
        <h3 className="text-h2 font-semibold text-slate-100 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-ops-humidity" />
          Spatial Neighbor Validation ({targetVariable})
        </h3>
        {targetStationId && (
          <span className="text-[11px] font-mono text-slate-400">
            Target [{targetStationId}]:{' '}
            <strong className="text-red-400 font-mono">
              {formatTemperature(targetValue, 1, true)}
            </strong>
          </span>
        )}
      </div>

      {neighbors.length === 0 ? (
        <div className="py-3 text-center text-slate-400 font-mono text-data italic">
          No contemporaneous spatial neighbors found within topological radius.
        </div>
      ) : (
        <div className="space-y-2.5">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse table-dense">
              <thead>
                <tr className="bg-surface-2/60 border-b border-border text-[10px] font-mono text-slate-400 uppercase">
                  <th className="py-1.5 px-2">Neighbor Station</th>
                  <th className="py-1.5 px-2 text-right">Distance</th>
                  <th className="py-1.5 px-2 text-right">Reading</th>
                  <th className="py-1.5 px-2 text-right">Delta</th>
                  <th className="py-1.5 px-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle text-[11px] font-mono">
                {neighbors.map((nb) => {
                  const deltaVal = nb.delta ?? (nb.observed_value !== undefined && targetValue !== undefined && nb.observed_value !== null && targetValue !== null ? targetValue - nb.observed_value : null);
                  const isPos = deltaVal !== null && deltaVal > 0;
                  return (
                    <tr key={nb.neighbor_station_id} className="hover:bg-surface-2/40">
                      <td className="py-1.5 px-2 font-semibold text-slate-200">
                        {nb.neighbor_station_id}
                      </td>
                      <td className="py-1.5 px-2 text-right text-slate-400">
                        {formatDistance(nb.distance_km)}
                      </td>
                      <td className="py-1.5 px-2 text-right text-slate-200">
                        {formatTemperature(nb.observed_value, 1, false)} {unit}
                      </td>
                      <td className="py-1.5 px-2 text-right font-medium">
                        {deltaVal !== null ? (
                          <span className={Math.abs(deltaVal) > 3.0 ? 'text-amber-400' : 'text-slate-300'}>
                            {isPos ? '+' : ''}{deltaVal.toFixed(1)} {unit}
                          </span>
                        ) : (
                          '--'
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-center">
                        {nb.is_consistent ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800">
                            <Check className="w-3 h-3" /> Corroborates
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-red-400 bg-red-950/60 px-1.5 py-0.5 rounded border border-red-800">
                            <X className="w-3 h-3" /> Discordant
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Consensus interpretation callout */}
          <div className="p-2 rounded bg-surface-2 border border-border-subtle flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">
              Spatial Consensus: <strong className={isIsolated ? 'text-red-400' : 'text-emerald-400'}>{isIsolated ? 'LOCAL_ONLY ISOLATION' : 'REGIONAL AGREEMENT'}</strong>
            </span>
            <span className="text-slate-400">
              Agreement: <strong className="text-slate-200">{agreeingCount}/{totalCount}</strong> stations
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
