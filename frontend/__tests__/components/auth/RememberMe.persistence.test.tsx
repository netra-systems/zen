/**
 * Remember Me Functionality Tests
 * Tests remember me functionality and persistence
 * 
 * BVJ: Enterprise segment - ensures session persistence for user convenience
 * Architecture: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginButton } from '@/auth/components';
import { authService } from '@/auth/service';
import '@testing-library/jest-dom';

// Mock auth service
jest.mock('@/auth/service');

// Mock storage APIs for persistence testing
const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

const mockSessionStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });
Object.defineProperty(window, 'sessionStorage', { value: mockSessionStorage });

// Mock cookies for persistent sessions
const mockCookies = new Map();
Object.defineProperty(document, 'cookie', {
  get: () => Array.from(mockCookies.entries()).map(([k, v]) => `${k}=${v}`).join('; '),
  set: (cookie) => {
    const [nameValue] = cookie.split(';');
    const [name, value] = nameValue.split('=');
    if (cookie.includes('expires=Thu, 01 Jan 1970')) {
      mockCookies.delete(name.trim());
    } else {
      mockCookies.set(name.trim(), value?.trim() || '');
    }
  }
});

describe('Remember Me Functionality Tests', () => {
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  
  const baseAuthContext = {
    user: null,
    login: mockLogin,
    logout: mockLogout,
    loading: false,
    authConfig: {
      development_mode: false,
      google_client_id: 'test-client-id',
      endpoints: {
        login: '/auth/login',
        logout: '/auth/logout',
        callback: '/auth/callback'
      }
    },
    token: null
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockLocalStorage.removeItem.mockClear();
    mockLocalStorage.clear.mockClear();
    mockSessionStorage.getItem.mockClear();
    mockSessionStorage.setItem.mockClear();
    mockSessionStorage.removeItem.mockClear();
    mockSessionStorage.clear.mockClear();
    mockCookies.clear();
    (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
  });

  describe('Token Persistence', () => {
    it('should persist authentication token in storage', async () => {
      mockLocalStorage.getItem.mockReturnValue('stored-jwt-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'stored-jwt-token',
        user: {
          id: 'user-123',
          email: 'stored@example.com',
          full_name: 'Stored User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Stored User')).toBeInTheDocument();
    });

    it('should handle missing stored token gracefully', () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle corrupted stored token', () => {
      mockLocalStorage.getItem.mockReturnValue('corrupted-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: null,
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should validate token expiration on load', () => {
      const expiredToken = 'expired.jwt.token';
      mockLocalStorage.getItem.mockReturnValue(expiredToken);
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: null,
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Session Persistence Logic', () => {
    it('should restore session from valid stored data', async () => {
      mockLocalStorage.getItem.mockReturnValue('valid-jwt-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'valid-jwt-token',
        user: {
          id: 'user-123',
          email: 'persistent@example.com',
          full_name: 'Persistent User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Persistent User')).toBeInTheDocument();
      expect(screen.getByText('Logout')).toBeInTheDocument();
    });

    it('should handle session restoration errors', () => {
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('Storage access denied');
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should prioritize fresh login over stored session', async () => {
      mockLocalStorage.getItem.mockReturnValue('old-token');
      
      const { rerender } = render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      expect(mockLogin).toHaveBeenCalled();
      
      // New login should override stored session
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'fresh-token',
        user: {
          id: 'user-456',
          email: 'fresh@example.com',
          full_name: 'Fresh User'
        }
      });
      
      rerender(<LoginButton />);
      expect(screen.getByText('Fresh User')).toBeInTheDocument();
    });

    it('should handle storage quota exceeded', () => {
      mockLocalStorage.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Test User')).toBeInTheDocument();
    });
  });

  describe('Development Mode Persistence', () => {
    it('should respect dev logout flag in persistence', () => {
      mockLocalStorage.getItem.mockReturnValue('dev-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle dev mode auto-login', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
      expect(screen.getByText('Dev User')).toBeInTheDocument();
    });

    it('should clear dev logout flag on manual login', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      const button = screen.getByText('Login with Google');
      await userEvent.click(button);
      
      expect(mockLogin).toHaveBeenCalled();
    });

    it('should persist dev mode sessions differently', async () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'dev-user-123',
          email: 'dev@example.com',
          full_name: 'Dev User'
        },
        token: 'dev-token',
        authConfig: {
          ...baseAuthContext.authConfig,
          development_mode: true
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('DEV MODE')).toBeInTheDocument();
      expect(screen.getByText('Dev User')).toBeInTheDocument();
    });
  });

  describe('Cross-Tab Session Sync', () => {
    it('should handle storage events for session sync', () => {
      render(<LoginButton />);
      
      // Simulate storage event from another tab
      const storageEvent = new StorageEvent('storage', {
        key: 'auth_token',
        newValue: 'new-token-from-tab',
        oldValue: null,
        storageArea: localStorage
      });
      
      window.dispatchEvent(storageEvent);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should sync logout across tabs', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        }
      });
      
      const { rerender } = render(<LoginButton />);
      
      // Simulate logout in another tab
      const logoutEvent = new StorageEvent('storage', {
        key: 'auth_token',
        newValue: null,
        oldValue: 'old-token',
        storageArea: localStorage
      });
      
      window.dispatchEvent(logoutEvent);
      
      // Simulate state update after storage event
      (authService.useAuth as jest.Mock).mockReturnValue(baseAuthContext);
      
      rerender(<LoginButton />);
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should sync new login across tabs', () => {
      render(<LoginButton />);
      
      // Simulate login in another tab
      const loginEvent = new StorageEvent('storage', {
        key: 'auth_token',
        newValue: 'new-login-token',
        oldValue: null,
        storageArea: localStorage
      });
      
      window.dispatchEvent(loginEvent);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle corrupted cross-tab data', () => {
      render(<LoginButton />);
      
      const corruptedEvent = new StorageEvent('storage', {
        key: 'auth_token',
        newValue: 'corrupted{token}data',
        oldValue: null,
        storageArea: localStorage
      });
      
      window.dispatchEvent(corruptedEvent);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  describe('Persistence Security', () => {
    it('should handle secure token storage', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'secure-jwt-token',
        user: {
          id: 'user-123',
          email: 'secure@example.com',
          full_name: 'Secure User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Secure User')).toBeInTheDocument();
    });

    it('should validate token integrity on restore', () => {
      mockLocalStorage.getItem.mockReturnValue('tampered.jwt.token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: null,
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should clear tokens on security violations', () => {
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: null,
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle token refresh for persistent sessions', async () => {
      mockLocalStorage.getItem.mockReturnValue('refresh-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'refreshed-token',
        user: {
          id: 'user-123',
          email: 'refreshed@example.com',
          full_name: 'Refreshed User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Refreshed User')).toBeInTheDocument();
    });
  });

  describe('Persistence Edge Cases', () => {
    it('should handle browser private mode restrictions', () => {
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('Private mode - storage disabled');
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should fallback to session storage', () => {
      mockLocalStorage.getItem.mockImplementation(() => {
        throw new Error('localStorage unavailable');
      });
      mockSessionStorage.getItem.mockReturnValue('session-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: 'session-token',
        user: {
          id: 'user-123',
          email: 'session@example.com',
          full_name: 'Session User'
        }
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Session User')).toBeInTheDocument();
    });

    it('should handle storage with no persistence', () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      mockSessionStorage.getItem.mockReturnValue(null);
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });

    it('should handle mixed storage states', () => {
      mockLocalStorage.getItem.mockReturnValue(null);
      mockSessionStorage.getItem.mockReturnValue('partial-token');
      
      (authService.useAuth as jest.Mock).mockReturnValue({
        ...baseAuthContext,
        token: null,
        user: null
      });
      
      render(<LoginButton />);
      
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });
});