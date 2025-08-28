import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '../providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';
import { webSocketService } from '../services/webSocketService';
import { logger } from '@/lib/logger';

// Mock the webSocketService
jest.mock('../services/webSocketService', () => ({
  webSocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    getSecureUrl: jest.fn((url) => url),
    onStatusChange: null,
    onMessage: null,
    updateToken: jest.fn()
  }
}));

jest.mock('@/lib/logger');
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

describe('WebSocket Parse Error Test', () => {
  const mockToken = 'test-auth-token';
  const mockAuthContext = {
    token: mockToken,
    user: null,
    login: jest.fn(),
    logout: jest.fn(),
    signUp: jest.fn(),
    forgotPassword: jest.fn(),
    resetPassword: jest.fn(),
    updateProfile: jest.fn(),
    isLoading: false,
    error: null
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset WebSocket mock state
    (webSocketService as any).onStatusChange = null;
    (webSocketService as any).onMessage = null;
  });

  it('should handle WebSocket parse error with code 1003 when receiving invalid message structure', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    let capturedOnError: ((error: any) => void) | undefined;

    // Mock the connect method to capture the error handler
    (webSocketService.connect as jest.Mock).mockImplementation((url, options) => {
      capturedOnError = options.onError;
      
      // Simulate connection and then invalid message after a short delay
      setTimeout(() => {
        // Trigger the parse error that we're seeing in production
        if (capturedOnError) {
          capturedOnError({
            code: 1003,
            message: 'Invalid message structure',
            timestamp: Date.now(),
            type: 'parse',
            recoverable: true
          });
        }
      }, 100);
    });

    const { container } = render(
      <AuthContext.Provider value={mockAuthContext}>
        <WebSocketProvider>
          <div>Test Content</div>
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    // Wait for the WebSocket connection to be established
    await waitFor(() => {
      expect(webSocketService.connect).toHaveBeenCalled();
    });

    // Wait for the error to be triggered
    await waitFor(() => {
      expect(logger.error).toHaveBeenCalledWith(
        'WebSocket connection error',
        undefined,
        expect.objectContaining({
          component: 'WebSocketProvider',
          action: 'connection_error',
          metadata: expect.objectContaining({
            error: 'Invalid message structure',
            type: 'parse',
            recoverable: true,
            code: 1003
          })
        })
      );
    }, { timeout: 500 });

    // Verify the error was logged with the exact structure we're seeing
    const errorCall = (logger.error as jest.Mock).mock.calls.find(
      call => call[0] === 'WebSocket connection error'
    );
    
    expect(errorCall).toBeDefined();
    expect(errorCall[2].metadata).toMatchObject({
      error: 'Invalid message structure',
      type: 'parse',
      recoverable: true,
      code: 1003
    });

    consoleSpy.mockRestore();
  });

  it('should fail validation when WebSocket message lacks required type and payload fields', async () => {
    let capturedOnMessage: ((message: any) => void) | undefined;
    let capturedOnError: ((error: any) => void) | undefined;

    // Mock the connect method to capture handlers
    (webSocketService.connect as jest.Mock).mockImplementation((url, options) => {
      capturedOnError = options.onError;
      // Simulate WebSocket service receiving the message
      (webSocketService as any).onMessage = options.onMessage;
      
      // Simulate receiving an invalid message structure
      setTimeout(() => {
        // This simulates what happens when validateWebSocketMessage returns null
        // because the message doesn't match the expected structure
        const invalidMessage = {
          // Missing 'type' and 'payload' fields that are required
          data: 'some random data',
          timestamp: new Date().toISOString()
        };
        
        // The service would trigger an error for invalid structure
        if (capturedOnError) {
          capturedOnError({
            code: 1003,
            message: 'Invalid message structure',
            timestamp: Date.now(),
            type: 'parse',
            recoverable: true
          });
        }
      }, 100);
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <WebSocketProvider>
          <div>Test Content</div>
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    // Wait for error to be logged
    await waitFor(() => {
      const errorCalls = (logger.error as jest.Mock).mock.calls;
      const parseError = errorCalls.find(call => 
        call[0] === 'WebSocket connection error' &&
        call[2]?.metadata?.code === 1003
      );
      expect(parseError).toBeDefined();
    }, { timeout: 500 });
  });

  it('should handle malformed JSON that causes parse error', async () => {
    let capturedOnError: ((error: any) => void) | undefined;

    // Mock the connect method
    (webSocketService.connect as jest.Mock).mockImplementation((url, options) => {
      capturedOnError = options.onError;
      
      // Simulate receiving malformed JSON that can't be parsed
      setTimeout(() => {
        // This simulates the catch block in webSocketService when JSON.parse fails
        if (capturedOnError) {
          capturedOnError({
            code: 1003,
            message: 'Failed to parse message',
            timestamp: Date.now(),
            type: 'parse',
            recoverable: true
          });
        }
      }, 100);
    });

    render(
      <AuthContext.Provider value={mockAuthContext}>
        <WebSocketProvider>
          <div>Test Content</div>
        </WebSocketProvider>
      </AuthContext.Provider>
    );

    // Wait for the parse error to be logged
    await waitFor(() => {
      const errorCalls = (logger.error as jest.Mock).mock.calls;
      const parseError = errorCalls.find(call => 
        call[2]?.metadata?.error === 'Failed to parse message' ||
        call[2]?.metadata?.error === 'Invalid message structure'
      );
      expect(parseError).toBeDefined();
    }, { timeout: 500 });
  });
});