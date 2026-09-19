import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { api, ApiError, API_BASE_URL, getToken, setToken as persistToken } from '../lib/apiClient';
import type { AuthUser } from '../lib/types';

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, role: 'participant' | 'organizer') => Promise<void>;
  setSession: (token: string, user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    api
      .get<AuthUser>('/api/auth/me')
      .then(setUser)
      .catch(() => persistToken(null))
      .finally(() => setIsLoading(false));
  }, []);

  const setSession = useCallback((token: string, newUser: AuthUser) => {
    persistToken(token);
    setUser(newUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      // OAuth2PasswordRequestForm on the backend expects a form-encoded
      // body (username/password), not JSON - handled directly here rather
      // than through the shared JSON api client.
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new ApiError(res.status, data.detail);
      }
      const data = await res.json();
      setSession(data.access_token, data.user);
    },
    [setSession]
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string, role: 'participant' | 'organizer') => {
      const data = await api.post<{ access_token: string; user: AuthUser }>('/api/auth/register', {
        email,
        password,
        full_name: fullName,
        role,
      });
      setSession(data.access_token, data.user);
    },
    [setSession]
  );

  const logout = useCallback(() => {
    persistToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, setSession, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
