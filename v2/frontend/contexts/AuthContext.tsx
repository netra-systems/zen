import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, AuthConfig } from '@/types';
import { getAuthConfig, devLogin, logout } from '@/services/authService';

interface AuthContextType {
  user: User | null;
  authConfig: AuthConfig | null;
  login: () => void;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const config = await getAuthConfig();
        setAuthConfig(config);

        if (config.development_mode) {
          const loggedInUser = await devLogin('dev@example.com');
          setUser(loggedInUser);
        } else if (config.user) {
          setUser(config.user);
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = () => {
    if (authConfig?.endpoints.login) {
      window.location.href = authConfig.endpoints.login;
    }
  };

  const handleLogout = async () => {
    if (authConfig?.endpoints.logout) {
      await logout();
      setUser(null);
      window.location.href = '/';
    }
  };

  return (
    <AuthContext.Provider value={{ user, authConfig, login, logout: handleLogout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};