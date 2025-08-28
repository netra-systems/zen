import React, { createContext, useContext, ReactNode } from 'react';
import { User } from '@/types/unified';

interface AuthContextType {
  user: User | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
  authConfig: any | null;
  token: string | null;
  initialized: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Use global mock state for consistency
const getMockAuthState = () => {
  return global.mockAuthState || {
    user: { id: 'test-user', email: 'test@example.com', full_name: 'Test User' },
    loading: false,
    authConfig: {
      development_mode: true,
      google_client_id: 'mock-google-client-id',
      endpoints: {
        login: 'http://localhost:8081/auth/login',
        logout: 'http://localhost:8081/auth/logout',
        callback: 'http://localhost:8081/auth/callback',
        token: 'http://localhost:8081/auth/token',
        user: 'http://localhost:8081/auth/me',
        dev_login: 'http://localhost:8081/auth/dev/login'
      }
    },
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature',
    isAuthenticated: true,
    initialized: true
  };
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const mockState = getMockAuthState();

  const login = async () => {
    // Mock login - update global state
    global.mockAuthState = {
      ...mockState,
      user: { id: 'test-user', email: 'test@example.com', full_name: 'Test User' },
      token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature',
      isAuthenticated: true,
      loading: false
    };
  };

  const logout = async () => {
    // Mock logout - update global state
    global.mockAuthState = {
      ...mockState,
      user: null,
      token: null,
      isAuthenticated: false,
      loading: false
    };
  };

  const contextValue = {
    ...mockState,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={contextValue}>
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