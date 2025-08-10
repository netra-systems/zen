import React, { ReactNode } from 'react';
import { AuthContext } from '@/auth/context';

interface MockAuthProviderProps {
  children: ReactNode;
  token?: string;
}

export const MockAuthProvider = ({ children, token = 'test-token' }: MockAuthProviderProps) => {
  const mockAuthValue = {
    token,
    user: { id: '1', email: 'test@example.com', name: 'Test User' },
    login: jest.fn(),
    logout: jest.fn(),
    isAuthenticated: true,
  };

  return (
    <AuthContext.Provider value={mockAuthValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const createWebSocketTestWrapper = (token?: string) => {
  return ({ children }: { children: ReactNode }) => (
    <MockAuthProvider token={token}>
      {children}
    </MockAuthProvider>
  );
};