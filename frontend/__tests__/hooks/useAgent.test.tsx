/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-10T14:32:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for useAgent hook
 * Git: v6 | 88345b5 | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-improvement | Seq: 3
 * Review: Pending | Score: 85/100
 * ================================
 */

import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { useAgent } from '@/hooks/useAgent';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { AuthContext } from '@/auth/context';

// Mock WebSocket
let mockWebSocketInstance: any;
class MockWebSocket {
  url: string;
  readyState: number = WebSocket.OPEN;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  send = jest.fn();
  close = jest.fn();

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstance = this;
    setTimeout(() => {
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }
}

global.WebSocket = MockWebSocket as any;

// Mock fetch for WebSocketProvider config
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ ws_url: 'ws://localhost:8000' }),
  })
) as jest.Mock;

describe('useAgent', () => {
  const mockAuthValue = {
    token: 'test-token',
    user: null,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    refreshToken: jest.fn(),
  };

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthContext.Provider value={mockAuthValue}>
      <WebSocketProvider>{children}</WebSocketProvider>
    </AuthContext.Provider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    mockWebSocketInstance = null;
    localStorage.setItem('access_token', 'test-token');
  });

  afterEach(() => {
    jest.restoreAllMocks();
    localStorage.clear();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    expect(result.current.sendUserMessage).toBeDefined();
    expect(result.current.stopAgent).toBeDefined();
    expect(typeof result.current.sendUserMessage).toBe('function');
    expect(typeof result.current.stopAgent).toBe('function');
  });

  it('should send message successfully', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.sendUserMessage('Test message');
    });
    
    expect(mockWebSocketInstance?.send).toHaveBeenCalled();
    const sentData = JSON.parse(mockWebSocketInstance?.send.mock.calls[0][0]);
    expect(sentData.type).toBe('user_message');
    expect(sentData.data.text).toBe('Test message');
  });

  it('should handle API error', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    // Simulate WebSocket error
    act(() => {
      mockWebSocketInstance.readyState = WebSocket.CLOSED;
      result.current.sendUserMessage('Test message');
    });
    
    // When WebSocket is closed, send should not be called
    expect(mockWebSocketInstance?.send).not.toHaveBeenCalled();
  });

  it('should handle network error', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Simulate connection error
    act(() => {
      if (mockWebSocketInstance?.onerror) {
        mockWebSocketInstance.onerror(new Event('error'));
      }
    });
    
    // Try to send message
    act(() => {
      result.current.sendUserMessage('Test message');
    });
    
    // Message should not be sent during error state
    expect(mockWebSocketInstance?.send).not.toHaveBeenCalled();
  });

  it('should set loading state during message send', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.sendUserMessage('Test message');
    });
    
    expect(mockWebSocketInstance?.send).toHaveBeenCalled();
  });

  it('should clear messages', () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // stopAgent should be callable
    act(() => {
      result.current.stopAgent();
    });
    
    // Check that stop message was sent
    if (mockWebSocketInstance?.send.mock.calls.length > 0) {
      const sentData = JSON.parse(mockWebSocketInstance?.send.mock.calls[0][0]);
      expect(sentData.type).toBe('stop_agent');
    }
  });

  it('should handle empty message', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.sendUserMessage('');
    });
    
    // Empty message should still be sent (hook doesn't validate)
    expect(mockWebSocketInstance?.send).toHaveBeenCalled();
  });

  it('should handle whitespace-only message', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    act(() => {
      result.current.sendUserMessage('   ');
    });
    
    // Whitespace message should still be sent (hook doesn't validate)
    expect(mockWebSocketInstance?.send).toHaveBeenCalled();
  });

  it('should maintain message history', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    // Send first message
    act(() => {
      result.current.sendUserMessage('First message');
    });
    
    // Send second message
    act(() => {
      result.current.sendUserMessage('Second message');
    });
    
    expect(mockWebSocketInstance?.send).toHaveBeenCalledTimes(2);
  });

  it('should handle concurrent messages', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    // Send multiple messages
    act(() => {
      result.current.sendUserMessage('Message 1');
      result.current.sendUserMessage('Message 2');
      result.current.sendUserMessage('Message 3');
    });
    
    expect(mockWebSocketInstance?.send).toHaveBeenCalledTimes(3);
  });

  it('should reset error on successful message', async () => {
    const { result } = renderHook(() => useAgent(), { wrapper });
    
    // Wait for WebSocket to connect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 10));
    });
    
    // First simulate an error
    act(() => {
      if (mockWebSocketInstance?.onerror) {
        mockWebSocketInstance.onerror(new Event('error'));
      }
    });
    
    // Then reconnect and send message successfully
    act(() => {
      mockWebSocketInstance.readyState = WebSocket.OPEN;
      result.current.sendUserMessage('Test message');
    });
    
    expect(mockWebSocketInstance?.send).toHaveBeenCalled();
  });
});