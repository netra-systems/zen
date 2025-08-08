import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getAuthConfig, getUser } from '@/services/auth';
import { AuthConfigResponse, User } from '@/types';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
  authConfig: AuthConfigResponse | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);

  useEffect(() => {
    async function loadAuthConfig() {
      try {
        const config = await getAuthConfig();
        setAuthConfig(config);
        if (config.development_mode) {
          setUser(config.user);
        }
      } catch (error) {
        console.error('Failed to load auth config:', error);
      } finally {
        setLoading(false);
      }
    }

    loadAuthConfig();
  }, []);

  const login = () => {
    if (authConfig) {
      window.location.href = authConfig.endpoints.login;
    }
  };

  const logout = () => {
    if (authConfig) {
      window.location.href = authConfig.endpoints.logout;
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, authConfig }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
