import { apiRequest } from './api';

export interface Conversation {
  conversation_id: string;
  title: string | null;
  pinned: boolean;
  last_active_at: string;
}

export function listConversations(): Promise<Conversation[]> {
  return apiRequest<Conversation[]>('/v1/conversations');
}

export function setConversationPinned(
  conversationId: string,
  pinned: boolean,
): Promise<Conversation> {
  return apiRequest<Conversation>(`/v1/conversations/${conversationId}`, {
    method: 'PATCH',
    body: { pinned },
  });
}

export function deleteConversation(conversationId: string): Promise<void> {
  return apiRequest<void>(`/v1/conversations/${conversationId}`, { method: 'DELETE' });
}
