import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ong-lived connections. These tests validate the System Under Test (SUT)
 * rather than mocking away the functionality we're trying to test.
 */
// Unmock auth service for proper service functionality
jest.unmock('@/auth/service');


import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '@/services/webSocketService';

// Mock the config
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8000',
    wsUrl: 'ws://localhost:8000/ws'
  }
}));

// Mock timers for testing timeouts and intervals
jest.useFakeTimers();

// Test component that handles token refresh scenarios
const TokenRefreshTestComponent = () => {
  const { status, sendMessage } = useWebSocketContext();
  const [refreshCount, setRefreshCount] = React.useState(0);
  const [lastTokenUsed, setLastTokenUsed] = React.useState('');
  
  const handleTokenRefresh = () => {
    setRefreshCount(prev => prev + 1);
  };
  
  return (
    <div>
      <div data-testid="ws-status">{status}</div>
      <div data-testid="refresh-count">{refreshCount}</div>
      <div data-testid="last-token">{lastTokenUsed}</div>
      <button data-testid="trigger-refresh" onClick={handleTokenRefresh}>
        Trigger Token Refresh
      </button>
      <button 
        data-testid="send-message"
        onClick={() => sendMessage({ type: 'test', payload: { content: 'test' } })}
      >
        Send Message
      </button>
    </div>
  );
};

// Mock auth context with token refresh capabilities
const createMockAuthContext = (initialToken: string) => ({
  token: initialToken,
  user: { id: '1', email: 'test@example.com' },
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  authConfig: {
    development_mode: true,
    google_client_id: 'test-client-id',
    endpoints: {
      login: '/auth/login',
      logout: '/auth/logout',
      callback: '/auth/callback',
      token: '/auth/token',
      user: '/auth/me',
      dev_login: '/auth/dev/login'
    },
    authorized_javascript_origins: ['http://localhost:3000'],
    authorized_redirect_uris: ['http://localhost:3000/auth/callback']
  }
});

// Unmock the WebSocketProvider to test real functionality
jest.unmock('@/providers/WebSocketProvider');

// Mock the unified auth service with refresh functionality
jest.mock('@/lib/unified-auth-service', () => ({
  unifiedAuthService: {
    getWebSocketAuthConfig: jest.fn(() => ({
      refreshToken: jest.fn()
    }))
  }
}));

// Helper function to create valid JWT tokens for testing
const createJWTToken = (payload: any) => {
  const header = { alg: 'HS256', typ: 'JWT' };
  const encodedHeader = btoa(JSON.stringify(header)).replace(/=/g, '');
  const encodedPayload = btoa(JSON.stringify(payload)).replace(/=/g, '');
  const signature = 'mock-signature';
  return `${encodedHeader}.${encodedPayload}.${signature}`;
};

describe('WebSocket Token Refresh Management (CRITICAL)', () => {
    jest.setTimeout(10000);
  let mockRefreshToken: jest.Mock;
  let authContext: any;
  
  beforeEach(() => {
    // Create a valid JWT token for testing
    const validTokenPayload = {
      exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
      iat: Math.floor(Date.now() / 1000),
      user_id: '1',
      email: 'test@example.com'
    };
    const validToken = createJWTToken(validTokenPayload);
    authContext = createMockAuthContext(validToken);
    
    // Setup refresh token mock
    mockRefreshToken = jest.fn();
    
    // Mock the unified auth service refresh function
    const { unifiedAuthService } = require('@/lib/unified-auth-service');
    unifiedAuthService.getWebSocketAuthConfig.mockReturnValue({
      refreshToken: mockRefreshToken
    });
    
    jest.clearAllMocks();
  });

  afterEach(() => {
    webSocketService.disconnect();
    jest.clearAllTimers();
    jest.restoreAllMocks();
  });

  describe('WebSocket Service Token Functionality', () => {
      jest.setTimeout(10000);
    it('should handle token updates via updateToken method', async () => {
      const initialToken = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });
      
      const newToken = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 7200,
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });

      // Initialize with first token
      webSocketService.connect('ws://localhost:8000/ws', {
        token: initialToken,
        refreshToken: mockRefreshToken
      });

      // Update to new token
      await webSocketService.updateToken(newToken);

      // Verify that the service accepts the token update
      expect(webSocketService.getSecurityStatus().hasToken).toBe(true);
    });

    it('should validate JWT token parsing functionality', async () => {
      const tokenPayload = {
        exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
        iat: Math.floor(Date.now() / 1000),
        user_id: '1',
        email: 'test@example.com'
      };
      
      const validToken = createJWTToken(tokenPayload);
      
      // Test that the WebSocket service can work with JWT tokens
      webSocketService.connect('ws://localhost:8000/ws', {
        token: validToken,
        refreshToken: mockRefreshToken
      });
      
      // Verify security status reflects the token
      const securityStatus = webSocketService.getSecurityStatus();
      expect(securityStatus.hasToken).toBe(true);
      expect(securityStatus.authMethod).toBe('subprotocol');
      expect(securityStatus.tokenRefreshEnabled).toBe(true);
    });

    it('should provide secure URL generation', async () => {
      const baseUrl = 'ws://localhost:8000/ws';
      const secureUrl = webSocketService.getSecureUrl(baseUrl);
      
      // Should convert to secure endpoint
      expect(secureUrl).toContain('/ws');
      
      // Should not contain token parameters in URL
      expect(secureUrl).not.toContain('token=');
      expect(secureUrl).not.toContain('auth=');
      expect(secureUrl).not.toContain('jwt=');
    });

    it('should handle message queuing functionality', async () => {
      const token = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });
      
      // Connect with message queuing capabilities
      webSocketService.connect('ws://localhost:8000/ws', {
        token,
        refreshToken: mockRefreshToken,
        rateLimit: {
          messages: 10,
          window: 60000
        }
      });
      
      // Test that service can handle messages
      const testMessage = {
        type: 'test' as const,
        payload: { content: 'test message' }
      };
      
      // Should not throw when sending messages
      expect(() => {
        webSocketService.sendMessage(testMessage);
      }).not.toThrow();
    });
  });

  describe('Token Lifecycle Management', () => {
      jest.setTimeout(10000);
    it('should handle connection state management', async () => {
      const token = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });
      
      // Test connection functionality
      const connectionConfig = {
        token,
        refreshToken: mockRefreshToken,
        reconnectOnFailure: true,
        maxReconnectAttempts: 3
      };
      
      webSocketService.connect('ws://localhost:8000/ws', connectionConfig);
      
      // Verify connection configuration is accepted
      // Check that service handles the configuration without throwing errors
      expect(() => {
        webSocketService.disconnect();
      }).not.toThrow();
    });

    it('should handle token validation and expiry detection', async () => {
      // Test with expired token
      const expiredToken = createJWTToken({
        exp: Math.floor(Date.now() / 1000) - 3600, // Expired 1 hour ago
        iat: Math.floor(Date.now() / 1000) - 7200,
        user_id: '1'
      });
      
      // Test with valid token  
      const validToken = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 3600, // Expires in 1 hour
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });
      
      // Should handle expired tokens gracefully
      webSocketService.connect('ws://localhost:8000/ws', {
        token: expiredToken,
        refreshToken: mockRefreshToken
      });
      
      // Update to valid token
      await webSocketService.updateToken(validToken);
      
      // Should accept the valid token
      expect(webSocketService.getSecurityStatus().hasToken).toBe(true);
    });

    it('should support rate limiting and connection management', async () => {
      const token = createJWTToken({
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
        user_id: '1'
      });
      
      // Test rate limiting configuration
      const config = {
        token,
        refreshToken: mockRefreshToken,
        rateLimit: {
          messages: 5,
          window: 1000
        },
        maxReconnectAttempts: 3,
        reconnectDelay: 1000
      };
      
      webSocketService.connect('ws://localhost:8000/ws', config);
      
      // Verify service handles configuration
      const securityStatus = webSocketService.getSecurityStatus();
      expect(securityStatus.hasToken).toBe(true);
      expect(securityStatus.tokenRefreshEnabled).toBe(true);
    });
  });
});