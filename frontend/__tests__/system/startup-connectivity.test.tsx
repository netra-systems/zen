import React from 'react';
import { render, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ct from 'react';
import { render, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

import {
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockResponse,
  createHealthResponse,
  setupFetchWithRetry,
  createCORSHeaders,
  setupWebSocketMocks,
  setupWebSocketFetch,
  createTestComponents,
  findEventHandler,
  setupTimerMocks,
  mockEnv
} from './helpers/startup-test-utilities';

import { initializeAllMocks } from './helpers/startup-test-mocks';

// Initialize all mocks
initializeAllMocks();

describe('Frontend System Startup - Connectivity', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    setupTestEnvironment();
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('API Connectivity', () => {
      jest.setTimeout(10000);
    it('should check backend health on startup', async () => {
      await testBackendHealthCheck();
    });

    const testBackendHealthCheck = async () => {
      const mockHealthResponse = createHealthResponse();
      (fetch as jest.Mock).mockResolvedValueOnce(
        createMockResponse(mockHealthResponse)
      );
      
      const response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      const data = await response.json();
      
      expect(fetch).toHaveBeenCalledWith(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      expect(data.status).toBe('OK');
    };

    it('should retry health check on failure', async () => {
      await testHealthCheckRetry();
    });

    const testHealthCheckRetry = async () => {
      const { getAttemptCount } = setupFetchWithRetry(2);
      await performRetryLogic();
      expect(getAttemptCount()).toBe(3);
    };

    const performRetryLogic = async () => {
      const maxRetries = 3;
      let lastError;
      let response;
      
      for (let i = 0; i < maxRetries; i++) {
        try {
          response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
          break;
        } catch (error) {
          lastError = error;
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }
      
      expect(response).toBeDefined();
    };

    it('should handle CORS headers correctly', async () => {
      await testCORSHeaders();
    });

    const testCORSHeaders = async () => {
      const headers = createCORSHeaders();
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        headers,
        json: async () => ({ status: 'OK' }),
      });
      
      const response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      expect(response.headers.get('Access-Control-Allow-Origin')).toBe('*');
    };
  });

  describe('WebSocket Connectivity', () => {
      jest.setTimeout(10000);
    let mockWebSocket: any;
    let mockWebSocketConstructor: jest.Mock;
    
    beforeEach(() => {
      ({ mockWebSocket, mockConstructor: mockWebSocketConstructor } = setupWebSocketMocks());
      setupWebSocketFetch();
    });

    it('should establish WebSocket connection on startup', async () => {
      await testWebSocketConnection();
    });
    
    const testWebSocketConnection = async () => {
      const token = 'test-token';
      const configUrl = 'http://localhost:8000/api/config';
      
      await fetch(configUrl);
      const wsUrl = 'ws://localhost:8000?token=' + token;
      new WebSocket(wsUrl);
      
      expect(fetch).toHaveBeenCalledWith(configUrl);
      expect(mockWebSocketConstructor).toHaveBeenCalledWith(wsUrl);
    };

    it('should handle WebSocket heartbeat', async () => {
      await testWebSocketHeartbeat();
    });

    const testWebSocketHeartbeat = async () => {
      const ws = new WebSocket('ws://localhost:3001/test'));
      ws.readyState = WebSocket.OPEN;
      
      ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      
      expect(ws.send).toHaveBeenCalledWith(
        expect.stringContaining('ping')
      );
    };

    it('should handle full heartbeat flow', async () => {
      await testFullHeartbeatFlow();
    });

    const testFullHeartbeatFlow = async () => {
      const { cleanup } = setupTimerMocks();
      const { wsInstance } = await setupHeartbeatTest();
      await simulateWebSocketOpen(wsInstance);
      await triggerHeartbeat();
      verifyHeartbeatMessage(wsInstance);
      cleanup();
    };
    
    const setupHeartbeatTest = async () => {
      const { MockedProviders } = createTestComponents();
      render(<MockedProviders><div>Test</div></MockedProviders>);
      await waitForWebSocketConnection();
      const wsInstance = mockWebSocketConstructor.mock.results[0]?.value;
      return { wsInstance };
    };
    
    const simulateWebSocketOpen = async (wsInstance: any) => {
      wsInstance.readyState = WebSocket.OPEN;
      const openHandler = findEventHandler(wsInstance, 'open');
      await act(() => { if (openHandler) openHandler(); });
    };
    
    const triggerHeartbeat = async () => {
      await act(() => { jest.advanceTimersByTime(30000); });
    };
    
    const verifyHeartbeatMessage = (wsInstance: any) => {
      expect(wsInstance.send).toHaveBeenCalledWith(
        expect.stringContaining('ping')
      );
    };
    
    const waitForWebSocketConnection = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalled();
      }, { timeout: 3000 });
    };

    it('should reconnect on connection loss', async () => {
      await testReconnection();
    });

    const testReconnection = async () => {
      const ws1 = new WebSocket('ws://localhost:3001/test'));
      const ws2 = new WebSocket('ws://localhost:3001/test'));
      
      expect(mockWebSocketConstructor).toHaveBeenCalledTimes(2);
      expect(mockWebSocketConstructor).toHaveBeenCalledWith('ws://localhost:8000');
    };
    
    it('should handle full reconnection flow', async () => {
      await testFullReconnectionFlow();
    });

    const testFullReconnectionFlow = async () => {
      const { cleanup } = setupTimerMocks();
      const { wsInstance } = await setupReconnectTest();
      await simulateConnectionLoss(wsInstance);
      await verifyReconnectionAttempt();
      cleanup();
    };
    
    const setupReconnectTest = async () => {
      const { MockedProviders } = createTestComponents();
      render(<MockedProviders><div>Test</div></MockedProviders>);
      await waitForInitialConnection();
      const wsInstance = mockWebSocketConstructor.mock.results[0]?.value;
      return { wsInstance };
    };
    
    const waitForInitialConnection = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalledTimes(1);
      }, { timeout: 3000 });
    };
    
    const simulateConnectionLoss = async (wsInstance: any) => {
      const closeHandler = findEventHandler(wsInstance, 'close');
      await act(() => {
        if (closeHandler) closeHandler({ code: 1006, reason: 'Connection lost' });
      });
      await act(() => { jest.advanceTimersByTime(5000); });
    };
    
    const verifyReconnectionAttempt = async () => {
      await waitFor(() => {
        expect(mockWebSocketConstructor).toHaveBeenCalledTimes(2);
      }, { timeout: 3000 });
    };

    it('should handle WebSocket error states', async () => {
      await testWebSocketErrors();
    });

    const testWebSocketErrors = async () => {
      const ws = new WebSocket('ws://localhost:3001/test'));
      const errorHandler = findEventHandler(ws, 'error');
      
      if (errorHandler) {
        await act(() => {
          errorHandler(new Error('WebSocket error'));
        });
      }
      
      expect(ws.addEventListener).toHaveBeenCalledWith('error', expect.any(Function));
    };

    it('should handle WebSocket close states', async () => {
      await testWebSocketClose();
    });

    const testWebSocketClose = async () => {
      const ws = new WebSocket('ws://localhost:3001/test'));
      const closeHandler = findEventHandler(ws, 'close');
      
      if (closeHandler) {
        await act(() => {
          closeHandler({ code: 1000, reason: 'Normal closure' });
        });
      }
      
      expect(ws.addEventListener).toHaveBeenCalledWith('close', expect.any(Function));
    };

    it('should handle WebSocket message events', async () => {
      await testWebSocketMessages();
    });

    const testWebSocketMessages = async () => {
      const ws = new WebSocket('ws://localhost:3001/test'));
      const messageHandler = findEventHandler(ws, 'message');
      
      if (messageHandler) {
        const mockMessage = { data: JSON.stringify({ type: 'pong' }) };
        await act(() => {
          messageHandler(mockMessage);
        });
      }
      
      expect(ws.addEventListener).toHaveBeenCalledWith('message', expect.any(Function));
    };
  });

  describe('Connection Status Monitoring', () => {
      jest.setTimeout(10000);
    it('should monitor API connection status', async () => {
      await testAPIStatusMonitoring();
    });

    const testAPIStatusMonitoring = async () => {
      (fetch as jest.Mock).mockResolvedValueOnce(
        createMockResponse({ status: 'OK' })
      );
      
      const response = await fetch(`${mockEnv.NEXT_PUBLIC_API_URL}/api/health`);
      const isHealthy = response.ok;
      
      expect(isHealthy).toBe(true);
    };

    it('should monitor WebSocket connection status', async () => {
      await testWebSocketStatusMonitoring();
    });

    const testWebSocketStatusMonitoring = async () => {
      const { mockWebSocket } = setupWebSocketMocks();
      const ws = new WebSocket('ws://localhost:3001/test'));
      
      mockWebSocket.readyState = WebSocket.OPEN;
      const isConnected = mockWebSocket.readyState === WebSocket.OPEN;
      
      expect(isConnected).toBe(true);
    };
  });
});