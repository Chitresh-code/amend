import { createContext, useContext, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ponytail: session check against GET /v1/auth/session lands with Epic C; until
// then every caller is treated as unauthenticated so route guards have something
// real to gate on.
const AuthContext = createContext<AuthState>({ isAuthenticated: false, isLoading: false });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state] = useState<AuthState>({ isAuthenticated: false, isLoading: false });
  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return null;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

export function RequireGuest({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  if (isAuthenticated) return <Navigate to="/chat" replace />;
  return <>{children}</>;
}
