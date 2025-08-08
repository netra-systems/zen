import { createContext, useContext, useEffect, ReactNode, useState, useCallback } from 'react';
import useAppStore from '@/store';
import { User } from '@/types';
import { Button } from '@/components/ui/button';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user, setUser, isLoading, setLoading } = useAppStore();
  const [authEndpoints, setAuthEndpoints] = useState<any>(null);

  const fetchEndpoints = useCallback(async () => {
    try {
      const response = await fetch('/api/v3/auth/endpoints');
      const data = await response.json();
      setAuthEndpoints(data);
      if (data.user) {
        setUser(data.user);
      } else if (data.development_mode) {
        // In dev mode, we might auto-login the dev user
        const devLoginResponse = await fetch(data.endpoints.dev_login, { method: 'POST' });
        if (devLoginResponse.ok) {
          const devUser = await devLoginResponse.json();
          setUser(devUser);
        }
      }
    } catch (error) {
      console.error("Failed to fetch auth endpoints:", error);
    }
  }, [setUser]);

  useEffect(() => {
    setLoading(true);
    fetchEndpoints().finally(() => setLoading(false));
  }, [fetchEndpoints, setLoading]);

  const login = () => {
    if (authEndpoints?.endpoints?.login) {
      window.location.href = authEndpoints.endpoints.login;
    }
  };

  const logout = async () => {
    if (authEndpoints?.endpoints?.logout) {
      await fetch(authEndpoints.endpoints.logout);
      setUser(null);
      // After logout, we might want to re-fetch endpoints to see if we should dev-login
      fetchEndpoints();
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading: isLoading }}>
      {isLoading ? (
        <div>Loading...</div>
      ) : user ? (
        children
      ) : (
        <div className="flex items-center justify-center h-screen">
          <Button onClick={login} size="lg">Login with Google</Button>
        </div>
      )}
    </AuthContext.Provider>
  );
}