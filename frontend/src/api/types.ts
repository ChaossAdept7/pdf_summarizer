// API Response Types

export interface UploadResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface ProcessingResult {
  filename: string;
  summary: string;
  page_count: number;
  processed_at: string;
  file_size?: number;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  result?: ProcessingResult;
  error?: string;
}

export interface HistoryItem {
  task_id: string;
  filename: string;
  summary: string;
  page_count: number;
  processed_at: string;
}

export interface HistoryResponse {
  documents: HistoryItem[];
  total: number;
}
