import axios from 'axios';
import type { UploadResponse, TaskStatusResponse, HistoryResponse } from './types';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000, // 10 second timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// API Functions

/**
 * Upload a PDF file for processing
 * @param file - PDF file to upload
 * @returns Upload response with task_id
 */
export const uploadPDF = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<UploadResponse>('/api/v1/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Get the status of a processing task
 * @param taskId - Task ID to check status for
 * @returns Task status with progress and result
 */
export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
  const response = await api.get<TaskStatusResponse>(`/api/v1/status/${taskId}`);
  return response.data;
};

/**
 * Get the history of processed documents (last 5)
 * @returns List of processed documents
 */
export const getHistory = async (): Promise<HistoryResponse> => {
  const response = await api.get<HistoryResponse>('/api/v1/history');
  return response.data;
};

export default api;
