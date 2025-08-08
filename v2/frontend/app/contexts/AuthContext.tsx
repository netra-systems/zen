'use client';

import { createContext, useContext, useEffect, ReactNode, useState, useCallback } from 'react';
import { User, AuthConfigResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { getAuthConfig, handleLogin as authLogin, handleLogout as authLogout } from '@/services/auth';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

const Header = ({ user, logout }: { user: User, logout: () => void }) => (
  <header className="flex justify-between items-center p-4 bg-gray-100 border-b">
    <div>Welcome, {user.full_name || user.email}</div>
    <Button onClick={logout}>Logout</Button>
  </header>
);

const LoginButton = ({ onLogin }: { onLogin: () => void }) => (
  <div className="flex items-center justify-center h-screen">
    <div className="text-center">
      <h1 className="text-3xl font-bold mb-8">Welcome to Netra</h1>
      <Button size="lg" onClick={onLogin}>
        Login with Google
      </Button>
    </div>
  </div>
);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfigResponse | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      const data = await getAuthConfig();
      setAuthConfig(data);
      if (data.user) {
        setUser(data.user);
      } else if (data.development_mode) {
        authLogin(data);
      }
    } catch (error) {
      console.error("Failed to fetch auth config:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = () => {
    authLogin(authConfig);
  };

  const logout = () => {
    authLogout(authConfig);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {loading ? (
        <div className="flex items-center justify-center h-screen">Loading...</div>
      ) : user ? (
        <>
          <Header user={user} logout={logout} />
          {children}
        </>
      ) : (
        <LoginButton onLogin={login} />
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
