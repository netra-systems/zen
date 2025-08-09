import React, { createContext, useContext, useState, ReactNode } from 'react';
import { User } from '@/types/User';

interface AuthContextType {
  user: User | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  setLoading: (loading: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>({ id: 'test-user', email: 'test@example.com', full_name: 'Test User' });
  const [loading, setLoading] = useState(false);

  const login = async () => {
    // Mock login
  };

  const logout = async () => {
    // Mock logout
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, setLoading }}>
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