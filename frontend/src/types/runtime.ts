export type DataSourceType =
  | 'SYNTHETIC_VALIDATION'
  | 'HISTORICAL_CSV'
  | 'OPEN_METEO'
  | 'IMD_AWS'
  | 'VISUAL_CROSSING';

export type RunMode =
  | 'SYNTHETIC_REPLAY'
  | 'HISTORICAL_ANALYSIS'
  | 'HISTORICAL_REPLAY'
  | 'LIVE_MONITORING';

export type TransportType = 'WEBSOCKET' | 'LOCAL' | 'REST';

export type RunStatus = 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'ERROR';

export interface RunContext {
  run_id: string;
  source_type: DataSourceType;
  source_name: string;
  mode: RunMode;
  dataset_id: string;
  dataset_version: string;
  station_count: number;
  observation_count: number;
  cadence: string;
  start_time?: string;
  end_time?: string;
  ground_truth_available: boolean;
  replay_speed: number;
  current_synthetic_time?: string;
  current_observation_index: number;
  transport: TransportType;
  database_target: string;
  created_at: string;
  status: RunStatus;
  metadata?: Record<string, any>;
}

export interface ProviderInfo {
  source_type: DataSourceType;
  name: string;
  configured: boolean;
  default_mode: RunMode;
  ground_truth_available: boolean;
  dataset_id: string;
  dataset_version: string;
  station_count: number;
  observation_count: number;
  cadence: string;
  description: string;
}

export interface CSVDatasetPreview {
  file_name: string;
  row_count: number;
  station_count: number;
  stations: string[];
  start_time?: string;
  end_time?: string;
  detected_cadence_minutes: number;
  missingness_pct: Record<string, number>;
  column_mapping: Record<string, string>;
  unmapped_columns: string[];
  missing_required_fields: string[];
  has_ground_truth: boolean;
  warnings: string[];
  sample_rows: Record<string, any>[];
}

export interface RunHistoryItem {
  run_id: string;
  source_type: DataSourceType;
  source_name: string;
  mode: RunMode;
  dataset_id: string;
  station_count: number;
  observation_count: number;
  created_at: string;
  status: RunStatus;
}
