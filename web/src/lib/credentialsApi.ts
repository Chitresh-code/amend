import { apiRequest } from './api';

export interface Credential {
  provider: string;
  model_id: string;
  configured: boolean;
  key_suffix: string;
  is_default: boolean;
  created_at: string;
}

export function listCredentials(): Promise<Credential[]> {
  return apiRequest<Credential[]>('/v1/credentials');
}

export function createCredential(
  provider: string,
  modelId: string,
  apiKey: string,
): Promise<Credential> {
  return apiRequest<Credential>('/v1/credentials', {
    method: 'POST',
    body: { provider, model_id: modelId, api_key: apiKey },
  });
}

export function setDefaultCredential(provider: string): Promise<Credential> {
  return apiRequest<Credential>(`/v1/credentials/${provider}`, {
    method: 'PATCH',
    body: { is_default: true },
  });
}

export function deleteCredential(provider: string): Promise<void> {
  return apiRequest<void>(`/v1/credentials/${provider}`, { method: 'DELETE' });
}
