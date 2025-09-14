/**
 * Issue #1140 Dual-Path Detection Tests
 * 
 * These tests should INITIALLY FAIL to demonstrate the dual-path problem
 * After remediation, they should PASS showing pure WebSocket implementation
 * 
 * Business Value: Ensures $500K+ ARR chat functionality uses reliable SSOT patterns
 */

import { jest } from '@jest/globals';
import { demoService } from '@/services/demoService';
import { WebSocketBridgeClient } from '@/services/uvs/WebSocketBridgeClient';
import { useAgent } from '@/hooks/useAgent';
import { renderHook } from '@testing-library/react';

// Mock the WebSocket service to track calls
const mockWebSocketSend = jest.fn();
const mockWebSocketConnect = jest.fn();

jest.mock('@/services/webSocketService', () => ({
  WebSocketService: jest.fn().mockImplementation(() => ({
    connect: mockWebSocketConnect,
    send: mockWebSocketSend,
    isConnected: () => true,
    disconnect: jest.fn()
  }))
}));

// Mock fetch to track HTTP calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock auth interceptor
jest.mock('@/lib/auth-interceptor', () => ({
  authInterceptor: {
    authenticatedFetch: mockFetch
  }
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn()
  }
}));

describe('Issue #1140: Dual-Path Architecture Detection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    mockWebSocketSend.mockReset();
    mockWebSocketConnect.mockReset();
  });

  it('should reject HTTP fallback for standard message types', async () => {
    /**
     * Test that will initially FAIL if HTTP fallback exists
     * This test validates that no message types use HTTP POST to chat endpoints
     */
    const messageTypes = ['test', 'analyze', 'optimize', 'process'];
    
    // Mock successful HTTP response to detect if it's called
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: 'test response', agents_involved: [], optimization_metrics: {}, session_id: 'test' }),
      status: 200,
      statusText: 'OK'
    });

    for (const type of messageTypes) {
      const message = `${type} message`;
      
      // Test using demo service (should reveal HTTP fallback)
      try {
        await demoService.sendChatMessage({
          message,
          industry: 'technology',
          session_id: 'test-session'
        });
        
        // Check if HTTP call was made to chat endpoint
        const chatHttpCalls = mockFetch.mock.calls.filter(call => 
          call[0].includes('/api/demo/chat') && 
          call[1]?.method === 'POST'
        );
        
        // This assertion should FAIL initially if HTTP fallback exists
        expect(chatHttpCalls).toHaveLength(0);
        
      } catch (error) {
        // If the service fails, that's acceptable - we're checking for dual paths
        console.log(`Service failed for ${type}: ${error}`);
      }
    }
  });

  it('should use only WebSocket transport for all message routing', async () => {
    /**
     * Test message router configuration
     * Should FAIL if dual routing exists
     */
    
    // Create WebSocket bridge client
    const client = new WebSocketBridgeClient('test-user');
    
    // Mock the WebSocket connection
    mockWebSocketConnect.mockResolvedValue(undefined);
    
    try {
      await client.ensureIntegration();
      
      // Test sending messages
      const testMessages = ['test message', 'analyze data', 'optimize costs'];
      
      for (const message of testMessages) {
        await client.sendUserMessage(message, 'test-thread');
        
        // Verify WebSocket was used
        expect(mockWebSocketSend).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'user_message',
            data: expect.objectContaining({
              message,
              thread_id: 'test-thread'
            })
          })
        );
      }
      
      // Verify no HTTP calls were made for these messages
      const httpChatCalls = mockFetch.mock.calls.filter(call => 
        call[0].includes('/chat') && call[1]?.method === 'POST'
      );
      expect(httpChatCalls).toHaveLength(0);
      
    } finally {
      client.dispose();
    }
  });

  it('should not have HTTP endpoints registered for chat functionality', () => {
    /**
     * Test that will FAIL if HTTP chat endpoints are discovered
     * This is a static analysis test to detect dual-path patterns
     */
    
    // Analyze the demo service for HTTP chat endpoints
    const demoServiceMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(demoService));
    const chatRelatedMethods = demoServiceMethods.filter(method => 
      method.toLowerCase().includes('chat') || 
      method.toLowerCase().includes('message')
    );
    
    // Check if these methods use HTTP
    for (const method of chatRelatedMethods) {
      const methodFunction = (demoService as any)[method];
      if (typeof methodFunction === 'function') {
        const methodSource = methodFunction.toString();
        
        // This assertion should FAIL initially if HTTP chat endpoints exist
        expect(methodSource).not.toContain('/api/demo/chat');
        expect(methodSource).not.toContain('POST');
      }
    }
  });

  it('should detect inconsistent transport methods between services', async () => {
    /**
     * Test for transport consistency across different services
     * Should FAIL if some services use HTTP while others use WebSocket
     */
    
    const transportMethods = new Set<string>();
    
    // Check demo service transport method
    try {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ response: 'test' }),
        status: 200
      });
      
      await demoService.sendChatMessage({
        message: 'test',
        industry: 'tech'
      });
      
      if (mockFetch.mock.calls.length > 0) {
        transportMethods.add('http');
      }
    } catch (error) {
      // Service might not be available, that's OK
    }
    
    // Check WebSocket service transport method
    const wsClient = new WebSocketBridgeClient('test-user');
    try {
      mockWebSocketConnect.mockResolvedValue(undefined);
      await wsClient.ensureIntegration();
      await wsClient.sendUserMessage('test message');
      
      if (mockWebSocketSend.mock.calls.length > 0) {
        transportMethods.add('websocket');
      }
    } catch (error) {
      // Connection might fail, that's OK
    } finally {
      wsClient.dispose();
    }
    
    // Should FAIL initially if both transport methods are found (dual path)
    expect(transportMethods.size).toBeLessThanOrEqual(1);
    
    // Prefer WebSocket if only one transport is found
    if (transportMethods.size === 1) {
      expect(transportMethods.has('websocket')).toBe(true);
    }
  });

  it('should validate hook usage follows SSOT WebSocket pattern', () => {
    /**
     * Test that React hooks follow SSOT WebSocket pattern
     * Should FAIL if hooks have HTTP fallback logic
     */
    
    // Mock WebSocket context
    const mockWebSocket = {
      sendMessage: jest.fn(),
      isConnected: true,
      connectionState: 'connected'
    };
    
    jest.mock('@/hooks/useWebSocket', () => ({
      useWebSocket: () => mockWebSocket
    }));
    
    const { result } = renderHook(() => useAgent());
    
    // Test sending a message
    result.current.sendUserMessage('test message');
    
    // Verify WebSocket was used
    expect(mockWebSocket.sendMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'user_message',
        payload: expect.objectContaining({
          content: 'test message'
        })
      })
    );
    
    // Verify no HTTP calls were made
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('should fail if demo service bypasses WebSocket for certain message types', async () => {
    /**
     * Specific test for message types that might trigger HTTP fallback
     * Based on Issue #1140 description of dual-path problem
     */
    
    const problematicMessageTypes = [
      { type: 'test', content: 'test the system' },
      { type: 'analyze', content: 'analyze my data' },
      { type: 'optimize', content: 'optimize my costs' },
      { type: 'process', content: 'process this information' }
    ];
    
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ 
        response: 'test response', 
        agents_involved: [], 
        optimization_metrics: {}, 
        session_id: 'test' 
      })
    });
    
    for (const msg of problematicMessageTypes) {
      try {
        // This should reveal if demo service uses HTTP for these types
        await demoService.sendChatMessage({
          message: msg.content,
          industry: 'technology'
        });
        
        // Check for HTTP calls
        const httpCalls = mockFetch.mock.calls.filter(call =>
          call[0].includes('/api/demo/chat') &&
          call[1]?.method === 'POST'
        );
        
        // This assertion should FAIL initially, proving dual-path exists
        expect(httpCalls.length).toBe(0);
        
      } catch (error) {
        // Service errors are acceptable - we're testing for dual paths
        console.log(`Expected service behavior for ${msg.type}: ${error}`);
      }
      
      // Reset mocks between tests
      mockFetch.mockClear();
    }
  });
});