/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-10T14:30:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for useWebSocket hook
 * Git: v6 | 88345b5 | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-improvement | Seq: 1
 * Review: Pending | Score: 85/100
 * ================================
 */

import { renderHook } from '@testing-library/react';
import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';

import { TestProviders } from '../test-utils/providers';// Mock the WebSocketProvider
jest.mock('@/providers/WebSocketProvider', () => ({
  WebSocketProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useWebSocketContext: jest.fn()
}));

describe('useWebSocket', () => {
  const mockSendMessage = jest.fn();
  const mockConnect = jest.fn();
  const mockDisconnect = jest.fn();
  const mockContext = {
    sendMessage: mockSendMessage,
    connect: mockConnect,
    disconnect: mockDisconnect,
    isConnected: true,
    connectionState: 'connected' as const,
    error: null,
    lastMessage: null,
    reconnectAttempts: 0,
    messageQueue: []
  };

  beforeEach(() => {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
    (useWebSocketContext as jest.Mock).mockReturnValue(mockContext);
  });

  it('should return WebSocket context values', () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current).toEqual(mockContext);
    expect(result.current.sendMessage).toBe(mockSendMessage);
    expect(result.current.isConnected).toBe(true);
  });

  it('should handle null context gracefully', () => {
    (useWebSocketContext as jest.Mock).mockReturnValue(null);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current).toBeNull();
  });

  it('should call sendMessage when invoked', () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    const message = { type: 'test', payload: { data: 'test' } };
    result.current.sendMessage(message);
    
    expect(mockSendMessage).toHaveBeenCalledWith(message);
    expect(mockSendMessage).toHaveBeenCalledTimes(1);
  });

  it('should reflect connection state changes', () => {
    const wrapper = TestProviders;
    
    const { result, rerender } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionState).toBe('connected');
    
    // Simulate disconnection
    (useWebSocketContext as jest.Mock).mockReturnValue({
      ...mockContext,
      isConnected: false,
      connectionState: 'disconnected'
    });
    
    rerender();
    
    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionState).toBe('disconnected');
  });

  it('should handle error states', () => {
    const errorContext = {
      ...mockContext,
      isConnected: false,
      connectionState: 'error' as const,
      error: new Error('WebSocket connection failed')
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(errorContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.error).toEqual(new Error('WebSocket connection failed'));
    expect(result.current.connectionState).toBe('error');
  });

  it('should handle reconnection attempts', () => {
    const reconnectingContext = {
      ...mockContext,
      isConnected: false,
      connectionState: 'reconnecting' as const,
      reconnectAttempts: 3
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(reconnectingContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.reconnectAttempts).toBe(3);
    expect(result.current.connectionState).toBe('reconnecting');
  });

  it('should handle message queue', () => {
    const queuedContext = {
      ...mockContext,
      messageQueue: [
        { type: 'message1', payload: {} },
        { type: 'message2', payload: {} }
      ]
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(queuedContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.messageQueue).toHaveLength(2);
    expect(result.current.messageQueue[0].type).toBe('message1');
  });

  it('should call connect method', () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    result.current.connect();
    
    expect(mockConnect).toHaveBeenCalledTimes(1);
  });

  it('should call disconnect method', () => {
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    result.current.disconnect();
    
    expect(mockDisconnect).toHaveBeenCalledTimes(1);
  });

  it('should handle last message updates', () => {
    const messageContext = {
      ...mockContext,
      lastMessage: {
        type: 'chat_message',
        payload: { text: 'Hello' },
        timestamp: Date.now()
      }
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(messageContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.lastMessage).toBeDefined();
    expect(result.current.lastMessage?.type).toBe('chat_message');
    expect(result.current.lastMessage?.payload).toEqual({ text: 'Hello' });
  });
});