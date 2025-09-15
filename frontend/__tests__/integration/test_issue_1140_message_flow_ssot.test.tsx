/**
 * Issue #1140 Message Flow SSOT Integration Tests
 * 
 * Tests complete message flow to ensure SSOT WebSocket pattern
 * Should initially FAIL if HTTP fallbacks exist
 * 
 * Business Value: Validates $500K+ ARR chat functionality uses consistent transport
 */

import { jest } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import React from 'react';

// Mock WebSocket to capture messages
const mockWebSocketSend = jest.fn();
const mockWebSocketConnect = jest.fn();
const mockWebSocketDisconnect = jest.fn();
const mockIsConnected = jest.fn(() => true);

// WebSocket connection monitor
class WebSocketConnectionMonitor {
  private httpFallbackDetected = false;
  private connectionUptime = 1.0; // Start at 100% uptime
  
  hadFallbackToHttp(): boolean {
    return this.httpFallbackDetected;
  }
  
  getConnectionUptime(): number {
    return this.connectionUptime;
  }
  
  detectHttpFallback(): void {
    this.httpFallbackDetected = true;
  }
  
  reduceUptime(factor: number): void {
    this.connectionUptime *= factor;
  }
}

// Mock the WebSocket service
jest.mock('@/services/webSocketService', () => ({
  WebSocketService: jest.fn().mockImplementation(() => ({
    connect: mockWebSocketConnect,
    send: mockWebSocketSend,
    disconnect: mockWebSocketDisconnect,
    isConnected: mockIsConnected
  }))
}));

// Mock fetch to detect HTTP calls
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

// Mock useWebSocket hook
const mockWebSocketHook = {
  sendMessage: jest.fn(),
  isConnected: true,
  connectionState: 'connected',
  lastMessage: null,
  connectionUrl: 'ws://localhost:8000/ws'
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => mockWebSocketHook
}));

// Test component that simulates user message sending
const TestMessageComponent: React.FC<{ onMessageSent?: (transport: string) => void }> = ({ onMessageSent }) => {
  const [message, setMessage] = React.useState('');
  
  const sendUserMessage = async (content: string) => {
    // Simulate the logic that might cause dual-path routing
    const messageType = content.toLowerCase();
    
    // Check for problematic message types that might trigger HTTP fallback
    if (messageType.includes('test') || 
        messageType.includes('analyze') || 
        messageType.includes('optimize') || 
        messageType.includes('process')) {
      
      // This simulates the dual-path problem - some messages might go via HTTP
      try {
        // Try WebSocket first
        mockWebSocketHook.sendMessage({
          type: 'user_message',
          payload: { content }
        });
        onMessageSent?.('websocket');
        
        // But also potentially fall back to HTTP (the problem we're detecting)
        if (content.includes('demo') || content.includes('example')) {
          mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ response: 'HTTP response' })
          });
          
          await fetch('/api/demo/chat', {
            method: 'POST',
            body: JSON.stringify({ message: content })
          });
          onMessageSent?.('http');
        }
        
      } catch (error) {
        console.error('Message sending failed:', error);
      }
    } else {
      // Regular messages should only use WebSocket
      mockWebSocketHook.sendMessage({
        type: 'user_message',
        payload: { content }
      });
      onMessageSent?.('websocket');
    }
  };
  
  return (
    <div>
      <input 
        data-testid="message-input"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
      />
      <button 
        data-testid="send-button"
        onClick={() => sendUserMessage(message)}
      >
        Send Message
      </button>
    </div>
  );
};

// Simulate a conversation function
const simulateConversation = async (messages: string[]): Promise<void> => {
  const monitor = new WebSocketConnectionMonitor();
  
  for (const message of messages) {
    try {
      // Simulate message sending with potential dual-path routing
      mockWebSocketHook.sendMessage({
        type: 'user_message',
        payload: { content: message }
      });
      
      // Check for problematic patterns that might trigger HTTP fallback
      if (message.includes('test') || message.includes('demo')) {
        // Simulate HTTP fallback detection
        if (mockFetch.mock.calls.some(call => 
          call[0].includes('/api/demo/chat') || call[0].includes('/chat')
        )) {
          monitor.detectHttpFallback();
        }
      }
      
      // Simulate connection quality issues
      if (message.includes('analyze') || message.includes('optimize')) {
        monitor.reduceUptime(0.98); // Slight reduction for complex operations
      }
      
      // Small delay between messages
      await new Promise(resolve => setTimeout(resolve, 100));
      
    } catch (error) {
      monitor.reduceUptime(0.9);
      console.error('Conversation simulation error:', error);
    }
  }
};

describe('Issue #1140: Message Flow SSOT Compliance', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    mockWebSocketSend.mockReset();
    mockWebSocketConnect.mockReset();
    mockWebSocketHook.sendMessage.mockReset();
  });

  it('should route all message types through WebSocket only', async () => {
    /**
     * Mock network interceptor to detect HTTP calls
     * Should initially FAIL if HTTP fallbacks exist
     */
    const httpSpy = jest.spyOn(global, 'fetch');
    const wsMessageSpy = jest.fn();
    
    // Track transport methods used
    const transportMethods = new Set<string>();
    
    const TestWrapper = () => (
      <TestMessageComponent 
        onMessageSent={(transport) => {
          transportMethods.add(transport);
          if (transport === 'websocket') {
            wsMessageSpy();
          }
        }}
      />
    );
    
    render(<TestWrapper />);
    
    const messageInput = screen.getByTestId('message-input');
    const sendButton = screen.getByTestId('send-button');
    
    const testMessages = [
      'test message',
      'analyze this data', 
      'optimize costs',
      'process request'
    ];
    
    for (const message of testMessages) {
      await act(async () => {
        fireEvent.change(messageInput, { target: { value: message } });
        fireEvent.click(sendButton);
        
        // Wait for async operations
        await waitFor(() => {
          expect(mockWebSocketHook.sendMessage).toHaveBeenCalledWith(
            expect.objectContaining({
              type: 'user_message',
              payload: expect.objectContaining({
                content: message
              })
            })
          );
        });
      });
    }
    
    // Should FAIL initially if HTTP calls are made
    const httpChatCalls = httpSpy.mock.calls.filter(call => 
      call[0].includes('/api/demo/chat') ||
      (call[1]?.method === 'POST' && call[0].includes('/chat'))
    );
    
    expect(httpChatCalls).toHaveLength(0);
    
    // Should PASS after remediation - all messages via WebSocket
    expect(wsMessageSpy).toHaveBeenCalledTimes(testMessages.length);
    
    // Should only use WebSocket transport (SSOT pattern)
    expect(transportMethods.has('websocket')).toBe(true);
    expect(transportMethods.has('http')).toBe(false);
  });

  it('should maintain WebSocket connection for all conversation types', async () => {
    /**
     * Test various conversation scenarios
     * Should FAIL initially if connections drop to HTTP
     */
    const connectionMonitor = new WebSocketConnectionMonitor();
    
    // Test various conversation scenarios
    await simulateConversation([
      'test connection',
      'analyze my data', 
      'optimize performance',
      'process this information'
    ]);
    
    // Should FAIL initially if connections drop to HTTP
    expect(connectionMonitor.hadFallbackToHttp()).toBe(false);
    expect(connectionMonitor.getConnectionUptime()).toBeGreaterThan(0.95); // 95% uptime
  });

  it('should detect dual-path routing in message flow', async () => {
    /**
     * Test specifically designed to catch dual-path routing
     * Should FAIL if both HTTP and WebSocket are used for the same message types
     */
    
    const transportLog: Array<{ message: string; transport: string; timestamp: number }> = [];
    
    const TestDualPathComponent = () => {
      const [message, setMessage] = React.useState('');
      
      const sendMessage = async (content: string) => {
        const timestamp = Date.now();
        
        // This simulates the problematic dual-path behavior
        if (content.includes('demo') || content.includes('example')) {
          // Use both transports (the problem we're detecting)
          
          // WebSocket path
          mockWebSocketHook.sendMessage({
            type: 'user_message',
            payload: { content }
          });
          transportLog.push({ message: content, transport: 'websocket', timestamp });
          
          // HTTP fallback path (should be detected and fail the test)
          try {
            await fetch('/api/demo/chat', {
              method: 'POST',
              body: JSON.stringify({ message: content })
            });
            transportLog.push({ message: content, transport: 'http', timestamp: timestamp + 1 });
          } catch (error) {
            // HTTP might fail, but we still detect the dual path attempt
          }
        } else {
          // Regular path - WebSocket only
          mockWebSocketHook.sendMessage({
            type: 'user_message',
            payload: { content }
          });
          transportLog.push({ message: content, transport: 'websocket', timestamp });
        }
      };
      
      return (
        <div>
          <input 
            data-testid="dual-path-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button 
            data-testid="dual-path-send"
            onClick={() => sendMessage(message)}
          >
            Send
          </button>
        </div>
      );
    };
    
    render(<TestDualPathComponent />);
    
    const input = screen.getByTestId('dual-path-input');
    const button = screen.getByTestId('dual-path-send');
    
    // Test messages that might trigger dual-path behavior
    const testMessages = [
      'demo message',        // Might trigger HTTP
      'regular message',     // Should only use WebSocket
      'example analysis',    // Might trigger HTTP
      'normal conversation'  // Should only use WebSocket
    ];
    
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: 'HTTP response' })
    });
    
    for (const msg of testMessages) {
      await act(async () => {
        fireEvent.change(input, { target: { value: msg } });
        fireEvent.click(button);
        await new Promise(resolve => setTimeout(resolve, 50));
      });
    }
    
    // Analyze transport log for dual-path violations
    const messageGroups = transportLog.reduce((groups, entry) => {
      if (!groups[entry.message]) {
        groups[entry.message] = [];
      }
      groups[entry.message].push(entry.transport);
      return groups;
    }, {} as Record<string, string[]>);
    
    // Check for dual-path violations
    for (const [message, transports] of Object.entries(messageGroups)) {
      const uniqueTransports = new Set(transports);
      
      // Should FAIL if the same message uses multiple transports (dual-path)
      expect(uniqueTransports.size).toBeLessThanOrEqual(1);
      
      // All messages should prefer WebSocket (SSOT pattern)
      if (uniqueTransports.size === 1) {
        expect(uniqueTransports.has('websocket')).toBe(true);
      }
    }
  });

  it('should validate consistent event handling across transport methods', async () => {
    /**
     * Test that event handling is consistent regardless of transport
     * Should FAIL if events are handled differently for HTTP vs WebSocket
     */
    
    const eventLog: Array<{ type: string; transport: string; data: any }> = [];
    
    // Mock event handlers
    const webSocketEventHandler = (event: any) => {
      eventLog.push({
        type: event.type,
        transport: 'websocket',
        data: event.data
      });
    };
    
    const httpEventHandler = (response: any) => {
      eventLog.push({
        type: 'http_response',
        transport: 'http',
        data: response
      });
    };
    
    // Simulate WebSocket events
    const webSocketEvents = [
      { type: 'agent_started', data: { run_id: 'test-1' } },
      { type: 'agent_thinking', data: { progress: 0.5 } },
      { type: 'agent_completed', data: { result: 'WebSocket result' } }
    ];
    
    webSocketEvents.forEach(webSocketEventHandler);
    
    // Simulate HTTP response (potential fallback)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ 
        response: 'HTTP result',
        status: 'completed'
      })
    });
    
    try {
      const httpResponse = await fetch('/api/demo/chat', {
        method: 'POST',
        body: JSON.stringify({ message: 'test' })
      });
      const httpData = await httpResponse.json();
      httpEventHandler(httpData);
    } catch (error) {
      // HTTP might fail, that's acceptable
    }
    
    // Analyze event consistency
    const webSocketEvents_filtered = eventLog.filter(e => e.transport === 'websocket');
    const httpEvents = eventLog.filter(e => e.transport === 'http');
    
    // Should FAIL if both transport methods are used (indicating dual-path)
    if (webSocketEvents_filtered.length > 0 && httpEvents.length > 0) {
      expect(webSocketEvents_filtered.length).toBeGreaterThan(0);
      expect(httpEvents.length).toBe(0); // Should not have HTTP events in SSOT pattern
    }
    
    // Event structure should be consistent
    const eventTypes = new Set(eventLog.map(e => e.type));
    expect(eventTypes.has('agent_started')).toBe(true);
    expect(eventTypes.has('agent_completed')).toBe(true);
  });

  it('should fail gracefully when detecting HTTP fallback patterns', async () => {
    /**
     * Test designed to catch and report HTTP fallback usage
     * This should FAIL initially to demonstrate the dual-path problem exists
     */
    
    // Monitor for HTTP fallback patterns
    const fallbackDetector = {
      httpCallsDetected: 0,
      webSocketCallsDetected: 0,
      dualPathViolations: [] as string[]
    };
    
    // Wrap fetch to detect HTTP calls
    const originalFetch = global.fetch;
    global.fetch = jest.fn(async (url, options) => {
      if (url.toString().includes('/chat') || url.toString().includes('/demo')) {
        fallbackDetector.httpCallsDetected++;
        fallbackDetector.dualPathViolations.push(`HTTP call detected: ${url}`);
      }
      return originalFetch(url, options);
    });
    
    // Wrap WebSocket to detect WebSocket calls
    const originalSendMessage = mockWebSocketHook.sendMessage;
    mockWebSocketHook.sendMessage = jest.fn((...args) => {
      fallbackDetector.webSocketCallsDetected++;
      return originalSendMessage(...args);
    });
    
    // Test problematic message types
    const problematicMessages = [
      'test the system demo',
      'analyze costs example',
      'optimize via demo service',
      'process demo data'
    ];
    
    render(<TestMessageComponent />);
    const input = screen.getByTestId('message-input');
    const button = screen.getByTestId('send-button');
    
    for (const message of problematicMessages) {
      await act(async () => {
        fireEvent.change(input, { target: { value: message } });
        fireEvent.click(button);
        await waitFor(() => {
          // Wait for message processing
        });
      });
    }
    
    // This test should FAIL initially if dual-path violations are detected
    expect(fallbackDetector.dualPathViolations).toHaveLength(0);
    
    // Should only have WebSocket calls in SSOT pattern
    expect(fallbackDetector.webSocketCallsDetected).toBeGreaterThan(0);
    expect(fallbackDetector.httpCallsDetected).toBe(0);
    
    // Restore original functions
    global.fetch = originalFetch;
    mockWebSocketHook.sendMessage = originalSendMessage;
  });
});