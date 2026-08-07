import { apiRequest } from './api';

export interface LoginResponse {
  user_id: string;
  email: string;
  organization: string | null;
}

export interface SessionResponse {
  user_id: string;
  email: string;
  organization: string | null;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/v1/auth/login', { method: 'POST', body: { email, password } });
}

export function logout(): Promise<void> {
  return apiRequest<void>('/v1/auth/logout', { method: 'POST' });
}

export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>('/v1/auth/session');
}
