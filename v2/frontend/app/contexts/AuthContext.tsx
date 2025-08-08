import { createContext, useContext, useEffect, ReactNode, useState, useCallback } from 'react';
import useAppStore from '@/store';
import { User } from '@/types';
import { Button } from '@/components/ui/button';
import { getAuthConfig } from '@/services/auth';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user, isLoading, devLogin, logout, fetchUser } = useAppStore();
  const [authEndpoints, setAuthEndpoints] = useState<any>(null);

  const fetchEndpoints = useCallback(async () => {
    try {
      const data = await getAuthConfig();
      setAuthEndpoints(data);
      if (data.user) {
        const token = document.cookie.split('; ').find(row => row.startsWith('access_token='))?.split('=')[1];
        if (token) {
          fetchUser(token);
        }
      } else if (data.development_mode) {
        devLogin();
      }
    } catch (error) {
      console.error("Failed to fetch auth endpoints:", error);
    }
  }, [devLogin, fetchUser]);

  useEffect(() => {
    fetchEndpoints();
  }, [fetchEndpoints]);

  const login = () => {
    if (authEndpoints?.endpoints?.login) {
      window.location.href = authEndpoints.endpoints.login;
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

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
