import React from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from './StateFeedback';

export interface ColumnDef<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  align?: 'left' | 'center' | 'right';
  width?: string;
}

interface MetricTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  selectedRowId?: string;
  rowIdKey?: keyof T;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (key: string) => void;
}

export function MetricTable<T>({
  columns,
  data,
  isLoading = false,
  emptyMessage = 'No telemetry records found.',
  onRowClick,
  selectedRowId,
  rowIdKey,
  sortColumn,
  sortDirection,
  onSort,
}: MetricTableProps<T>) {
  if (isLoading) {
    return <LoadingSkeleton rows={5} height="h-10" />;
  }

  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="w-full overflow-x-auto rounded border border-border bg-surface-1">
      <table className="w-full text-left border-collapse table-dense">
        <thead>
          <tr className="bg-surface-2/70 border-b border-border">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`py-2 px-3 text-[11px] font-mono text-slate-400 uppercase tracking-wider ${
                  col.sortable ? 'cursor-pointer select-none hover:text-slate-200' : ''
                } ${col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'}`}
                style={{ width: col.width }}
                onClick={() => col.sortable && onSort && onSort(col.key)}
              >
                <div
                  className={`inline-flex items-center gap-1 ${
                    col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : 'justify-start'
                  }`}
                >
                  <span>{col.header}</span>
                  {col.sortable && sortColumn === col.key && (
                    <span>
                      {sortDirection === 'asc' ? (
                        <ChevronUp className="w-3.5 h-3.5 text-ops-weather" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-ops-weather" />
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {data.map((row, idx) => {
            const rowId = rowIdKey ? String(row[rowIdKey]) : String(idx);
            const isSelected = selectedRowId === rowId;

            return (
              <tr
                key={rowId}
                onClick={() => onRowClick && onRowClick(row)}
                className={`transition-colors ${
                  onRowClick ? 'cursor-pointer hover:bg-surface-hover/80' : ''
                } ${isSelected ? 'bg-surface-2 border-l-2 border-l-ops-weather' : 'hover:bg-surface-2/40'}`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-2 px-3 text-data text-slate-200 ${
                      col.align === 'right' ? 'text-right font-mono' : col.align === 'center' ? 'text-center' : 'text-left'
                    }`}
                  >
                    {col.render
                      ? col.render(row)
                      : String((row as Record<string, unknown>)[col.key] ?? '--')}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
