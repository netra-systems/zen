import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import useAppStore from '@/store';
import { User } from '@/types';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const user = useAppStore((state) => state.user);
  const devLogin = useAppStore((state) => state.devLogin);
  const logout = useAppStore((state) => state.logout);
  const isLoading = useAppStore((state) => state.isLoading);

  const login = () => {
    devLogin();
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading: isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}