// API 타입 정의

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled';

export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface NodeState {
  status: NodeStatus;
  startTime?: number;
  endTime?: number;
  retryCount?: number;
}

export interface NodeStates {
  [nodeId: string]: NodeState;
}

export interface NodeResults {
  [nodeId: string]: string | object | null;
}

export interface JobItem {
  id: string;
  image_path: string;
  image_name: string;
  status: JobStatus;
  current_node?: string;
  progress: number;
  result?: PipelineResult;
  error?: string;
  created_at: string;
  updated_at: string;
  node_states?: NodeStates;
  node_results?: NodeResults;
}

export interface BatchJob {
  id: string;
  items: JobItem[];
  status: JobStatus;
  total: number;
  completed: number;
  failed: number;
  created_at: string;
  updated_at: string;
}

export interface PipelineConfig {
  provider: string;
  model: string;
  temperature: number;
  config_path?: string;
}

export interface PipelineResult {
  image_path: string;
  html_table: string;
  synthetic_table: string;
  synthetic_json: Record<string, unknown>;
  qa_results: QAPair[];
}

export interface QAPair {
  question: string;
  answer: string;
  reasoning?: string;
}

export interface WebSocketMessage {
  type: 'item_start' | 'item_complete' | 'item_error' | 'batch_complete' | 'progress';
  item_id?: string;
  image_name?: string;
  result?: PipelineResult;
  error?: string;
  job_id?: string;
  completed?: number;
  failed?: number;
  total?: number;
  progress?: number;
  current_node?: string;
  nodes?: NodeStates;
  node_results?: NodeResults;
  retry_count?: number;
}
