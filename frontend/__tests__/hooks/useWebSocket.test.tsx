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
  const mockContext = {
    status: 'OPEN' as const,
    messages: [],
    sendMessage: mockSendMessage
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
    expect(result.current.status).toBe('OPEN');
  });

  it('should throw error when used outside of provider', () => {
    // Mock useWebSocketContext to throw error as per actual implementation
    (useWebSocketContext as jest.Mock).mockImplementation(() => {
      throw new Error('useWebSocketContext must be used within a WebSocketProvider');
    });
    
    const wrapper = TestProviders;
    
    // Should throw when trying to use outside provider context
    expect(() => {
      renderHook(() => useWebSocket(), { wrapper });
    }).toThrow('useWebSocketContext must be used within a WebSocketProvider');
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
    
    expect(result.current.status).toBe('OPEN');
    
    // Simulate disconnection
    (useWebSocketContext as jest.Mock).mockReturnValue({
      ...mockContext,
      status: 'CLOSED'
    });
    
    rerender();
    
    expect(result.current.status).toBe('CLOSED');
  });

  it('should handle closing states', () => {
    const closingContext = {
      ...mockContext,
      status: 'CLOSING' as const
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(closingContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.status).toBe('CLOSING');
  });

  it('should handle connecting state', () => {
    const connectingContext = {
      ...mockContext,
      status: 'CONNECTING' as const
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(connectingContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.status).toBe('CONNECTING');
  });

  it('should handle messages array', () => {
    const messagesContext = {
      ...mockContext,
      messages: [
        { type: 'message1', payload: {} },
        { type: 'message2', payload: {} }
      ]
    };
    
    (useWebSocketContext as jest.Mock).mockReturnValue(messagesContext);
    
    const wrapper = TestProviders;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].type).toBe('message1');
  });

  it('should handle all WebSocket states', () => {
    const wrapper = TestProviders;
    const states = ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'] as const;
    
    states.forEach(state => {
      (useWebSocketContext as jest.Mock).mockReturnValue({
        ...mockContext,
        status: state
      });
      
      const { result } = renderHook(() => useWebSocket(), { wrapper });
      expect(result.current.status).toBe(state);
    });
  });

  it('should accumulate messages over time', () => {
    const wrapper = TestProviders;
    
    // Start with no messages
    const { result, rerender } = renderHook(() => useWebSocket(), { wrapper });
    expect(result.current.messages).toHaveLength(0);
    
    // Add first message
    (useWebSocketContext as jest.Mock).mockReturnValue({
      ...mockContext,
      messages: [{ type: 'chat_message', payload: { text: 'Hello' } }]
    });
    rerender();
    expect(result.current.messages).toHaveLength(1);
    
    // Add second message
    (useWebSocketContext as jest.Mock).mockReturnValue({
      ...mockContext,
      messages: [
        { type: 'chat_message', payload: { text: 'Hello' } },
        { type: 'status_update', payload: { status: 'processing' } }
      ]
    });
    rerender();
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].type).toBe('status_update');
  });
});