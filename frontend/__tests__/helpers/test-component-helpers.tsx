/**
 * Test Component Helpers - Reusable test components
 * Keeps test functions ≤8 lines by extracting common component patterns
 */

import React from 'react';
import { WebSocketContext } from '@/providers/WebSocketProvider';
import { useAuthStore } from '@/store/authStore';
import { createTestUser } from './test-setup-helpers';

export const WebSocketStatusComponent = () => {
  const wsContext = React.useContext(WebSocketContext);
  const status = wsContext?.status || 'CLOSED';
  return <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>;
};

export const AuthenticatedWebSocketComponent = () => {
  const wsContext = React.useContext(WebSocketContext);
  const status = wsContext?.status || 'CLOSED';
  const login = useAuthStore((state) => state.login);
  
  return (
    <div>
      <div data-testid="ws-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
      <button onClick={() => login(createTestUser(), 'new-token')}>Login</button>
    </div>
  );
};

export const ConnectionRecoveryComponent = () => {
  const [status, setStatus] = React.useState<'OPEN' | 'CLOSED'>('CLOSED');
  
  return (
    <div>
      <div data-testid="connection-status">{status === 'OPEN' ? 'Connected' : 'Disconnected'}</div>
      <button onClick={() => setStatus('OPEN')}>Reconnect</button>
      <button onClick={() => setStatus('CLOSED')}>Disconnect</button>
    </div>
  );
};

export const AuthStatusComponent = () => {
  const logout = useAuthStore((state) => state.logout);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  React.useEffect(() => {
    checkTokenExpiry(logout);
  }, [logout]);
  
  return <div data-testid="auth-status">{isAuthenticated ? 'Authenticated' : 'Session Expired'}</div>;
};

export const CacheManagementComponent = () => {
  const [cacheSize, setCacheSize] = React.useState(100);
  
  return (
    <div>
      <div data-testid="cache-size">{cacheSize}</div>
      <button onClick={() => setCacheSize(0)}>Clear Cache</button>
    </div>
  );
};

export const TaskRetryComponent = () => {
  const [retryCount, setRetryCount] = React.useState(0);
  const [status, setStatus] = React.useState('idle');
  
  React.useEffect(() => {
    executeRetryTask(setStatus, setRetryCount);
  }, []);
  
  return (
    <div>
      <div data-testid="retry-count">{retryCount}</div>
      <div data-testid="status">{status}</div>
    </div>
  );
};

const checkTokenExpiry = (logout: () => void) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp * 1000 < Date.now()) logout();
    } catch {
      logout();
    }
  }
};

const executeRetryTask = async (setStatus: (status: string) => void, setRetryCount: (count: number) => void) => {
  setStatus('retrying');
  for (let i = 0; i < 3; i++) {
    await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 100));
    setRetryCount(i + 1);
  }
  setStatus('completed');
};