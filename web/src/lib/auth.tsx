import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getSession, logout as apiLogout, type SessionResponse } from './authApi';

interface AuthState {
  status: 'loading' | 'authenticated' | 'unauthenticated';
  user: SessionResponse | null;
  // Where RequireGuest sends an authenticated visitor away from /login.
  // Owning this as state (rather than a separate imperative navigate() call
  // from the login form) means there is exactly one place deciding the
  // post-login destination, instead of two redirects racing each other.
  postLoginPath: string;
}

interface AuthContextValue extends AuthState {
  setUser: (user: SessionResponse, postLoginPath?: string) => void;
  completeCredentialSetup: () => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    status: 'loading',
    user: null,
    postLoginPath: '/chat',
  });

  useEffect(() => {
    getSession()
      .then((user) => setState((s) => ({ ...s, status: 'authenticated', user })))
      .catch(() => setState((s) => ({ ...s, status: 'unauthenticated', user: null })));
  }, []);

  const setUser = (user: SessionResponse, postLoginPath: string = '/chat') =>
    setState({ status: 'authenticated', user, postLoginPath });

  const completeCredentialSetup = () => setState((s) => ({ ...s, postLoginPath: '/chat' }));

  const logout = async () => {
    await apiLogout();
    setState({ status: 'unauthenticated', user: null, postLoginPath: '/chat' });
  };

  return (
    <AuthContext.Provider value={{ ...state, setUser, completeCredentialSetup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();
  if (status === 'loading') return null;
  if (status === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export function RequireGuest({ children }: { children: ReactNode }) {
  const { status, postLoginPath } = useAuth();
  if (status === 'loading') return null;
  if (status === 'authenticated') return <Navigate to={postLoginPath} replace />;
  return <>{children}</>;
}
