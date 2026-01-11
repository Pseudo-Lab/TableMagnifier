import { BatchJob, PipelineConfig } from './types';

const API_BASE = '';

export async function uploadImages(files: File[]): Promise<string[]> {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) throw new Error('Upload failed');
  
  const data = await response.json();
  return data.paths;
}

export async function runPipeline(imagePaths: string[], config?: PipelineConfig): Promise<{ job_id: string; total: number }> {
  const response = await fetch(`${API_BASE}/api/pipeline/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_paths: imagePaths, config }),
  });
  
  if (!response.ok) throw new Error('Failed to start pipeline');
  
  return response.json();
}

export async function getJobStatus(jobId: string): Promise<BatchJob> {
  const response = await fetch(`${API_BASE}/api/pipeline/status/${jobId}`);
  
  if (!response.ok) throw new Error('Failed to get job status');
  
  return response.json();
}

export async function pauseJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/pipeline/pause/${jobId}`, {
    method: 'POST',
  });
  
  if (!response.ok) throw new Error('Failed to pause job');
}

export async function resumeJob(jobId: string, config?: PipelineConfig): Promise<void> {
  const response = await fetch(`${API_BASE}/api/pipeline/resume/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config || {}),
  });
  
  if (!response.ok) throw new Error('Failed to resume job');
}

export async function retryFailed(jobId: string, itemIds?: string[]): Promise<void> {
  const response = await fetch(`${API_BASE}/api/pipeline/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, item_ids: itemIds }),
  });
  
  if (!response.ok) throw new Error('Failed to retry');
}

export async function cancelJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/pipeline/cancel/${jobId}`, {
    method: 'POST',
  });
  
  if (!response.ok) throw new Error('Failed to cancel job');
}

export async function listJobs(): Promise<{ jobs: Array<{ id: string; status: string; total: number; completed: number; failed: number; created_at: string }> }> {
  const response = await fetch(`${API_BASE}/api/pipeline/list`);
  
  if (!response.ok) throw new Error('Failed to list jobs');
  
  return response.json();
}

export function createWebSocket(jobId: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/ws/${jobId}`);
}
