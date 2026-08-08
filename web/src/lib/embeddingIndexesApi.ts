import { apiRequest } from './api';

export interface EmbeddingIndex {
  embedding_model_id: string;
  provider: string;
  model_id: string;
  status: 'registered' | 'building' | 'ready';
  clause_count: number;
  is_default: boolean;
}

export function listEmbeddingIndexes(): Promise<EmbeddingIndex[]> {
  return apiRequest<EmbeddingIndex[]>('/v1/embedding-indexes');
}

export function registerEmbeddingIndex(
  provider: string,
  modelId: string,
  dimension: number,
): Promise<EmbeddingIndex> {
  return apiRequest<EmbeddingIndex>('/v1/embedding-indexes', {
    method: 'POST',
    body: { provider, model_id: modelId, dimension },
  });
}

export function setDefaultEmbeddingIndex(embeddingModelId: string): Promise<EmbeddingIndex> {
  return apiRequest<EmbeddingIndex>(
    `/v1/embedding-indexes/${encodeURIComponent(embeddingModelId)}`,
    { method: 'PATCH', body: { is_default: true } },
  );
}
