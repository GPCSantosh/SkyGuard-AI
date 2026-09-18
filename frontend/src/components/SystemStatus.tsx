import React from 'react';
import { SystemHealthStatus, SystemComponentHealth } from '../types/api';

interface SystemStatusProps {
  health?: SystemHealthStatus;
  isLoading?: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ health, isLoading }) => {
  if (isLoading) {
    return (
      <div className="bg-[#0D131F] border border-[#1E293B] rounded p-4 text-xs font-mono text-[#94A3B8] animate-pulse">
        Polling inference pipeline diagnostics...
      </div>
    );
  }

  const components: SystemComponentHealth[] = health?.components ?? [];

  return (
    <div className="bg-[#0D131F] border border-[#1E293B] rounded overflow-hidden">
      <div className="p-3 bg-[#111827] border-b border-[#1E293B] flex items-center justify-between">
        <h3 className="font-mono text-xs font-bold text-[#F8FAFC] uppercase tracking-wider">
          Diagnostic Pipeline Telemetry
        </h3>
        <span className="font-mono text-[11px] text-[#64748B]">
          Sub-50ms Hybrid Inference SLA
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="border-b border-[#1E293B] text-[10px] text-[#64748B] bg-[#0A0E17] uppercase">
              <th className="py-2 px-3.5">Subsystem</th>
              <th className="py-2 px-3.5">Status</th>
              <th className="py-2 px-3.5">Details</th>
              <th className="py-2 px-3.5 text-right">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E293B]/60">
            {components.map((comp: SystemComponentHealth) => {
              const isOk = comp.status === 'OK';
              const isWarn = comp.status === 'WARN';
              return (
                <tr key={comp.name} className="hover:bg-[#111827] transition-colors">
                  <td className="py-2.5 px-3.5 font-semibold text-[#F8FAFC]">
                    {comp.name}
                  </td>
                  <td className="py-2.5 px-3.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-bold uppercase ${
                        isOk
                          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80'
                          : isWarn
                          ? 'bg-amber-950/60 text-amber-300 border-amber-800/80'
                          : 'bg-red-950/60 text-red-300 border-red-800/80'
                      }`}
                    >
                      <span>{comp.status}</span>
                    </span>
                  </td>
                  <td className="py-2.5 px-3.5 text-[#94A3B8] text-[11px]">
                    {comp.details}
                  </td>
                  <td className="py-2.5 px-3.5 text-right text-[#38BDF8] font-semibold">
                    {comp.latency_ms !== undefined ? `${comp.latency_ms.toFixed(2)} ms` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
