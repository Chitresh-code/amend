import { apiRequest } from './api';

export interface ApiKey {
  id: string;
  label: string;
  key_suffix: string;
  created_at: string;
}

export function listApiKeys(): Promise<ApiKey[]> {
  return apiRequest<ApiKey[]>('/v1/api-keys');
}

export function revokeApiKey(id: string): Promise<void> {
  return apiRequest<void>(`/v1/api-keys/${id}`, { method: 'DELETE' });
}
