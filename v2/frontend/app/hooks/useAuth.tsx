
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import useAppStore from '@/store';

interface AuthContextType {
  isAuthenticated: boolean;
  isAuthReady: boolean; // Add this line
  user: Record<string, unknown> | null;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { token, user, setToken, fetchUser, clearAuth } = useAppStore();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isAuthReady, setIsAuthReady] = useState<boolean>(false); // Add this line

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken && !token) {
      setToken(storedToken);
      fetchUser(storedToken);
    }
    setIsAuthenticated(!!storedToken);
    setIsAuthReady(true); // Set auth as ready
  }, [token, setToken, fetchUser]);

  const login = () => {
    window.location.href = 'http://localhost:8000/api/v3/auth/login/google';
  };

  const logout = () => {
    clearAuth();
    localStorage.removeItem('authToken');
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isAuthReady, user, login, logout }}>
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
