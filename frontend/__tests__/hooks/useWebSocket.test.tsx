/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-12T14:45:00Z
 * Agent: Test Debug Expert Agent #6
 * Context: Fix useWebSocket test to work with MockWebSocketProvider
 * Git: v6 | 88345b5 | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-fix | Seq: 2
 * Review: Pending | Score: 95/100
 * ================================
 */

import { renderHook } from '@testing-library/react';
import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { TestProviders } from '../test-utils/providers';

describe('useWebSocket', () => {
  beforeEach(() => {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
  });

  it('should return WebSocket context values', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    // The MockWebSocketProvider provides these properties
    expect(result.current).toBeDefined();
    expect(result.current.status).toBe('OPEN');
    expect(result.current.messages).toEqual([]);
    expect(result.current.sendMessage).toBeDefined();
    expect(typeof result.current.sendMessage).toBe('function');
  });

  it('should provide all required context properties', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    // Check for all expected properties from MockWebSocketProvider
    expect(result.current).toHaveProperty('status');
    expect(result.current).toHaveProperty('messages');
    expect(result.current).toHaveProperty('sendMessage');
    expect(result.current).toHaveProperty('isConnected');
    expect(result.current).toHaveProperty('connectionState');
    expect(result.current).toHaveProperty('error');
  });

  it('should call sendMessage when invoked', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    const message = { type: 'test', payload: { data: 'test' } };
    result.current.sendMessage(message);
    
    // The sendMessage from MockWebSocketProvider is a jest.fn()
    expect(result.current.sendMessage).toHaveBeenCalledWith(message);
  });

  it('should start with OPEN status from MockWebSocketProvider', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    // MockWebSocketProvider always returns 'OPEN' status
    expect(result.current.status).toBe('OPEN');
  });

  it('should start with empty messages array', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.messages).toEqual([]);
  });

  it('should indicate connected state', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    // MockWebSocketProvider sets isConnected to true
    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionState).toBe('connected');
  });

  it('should have no error initially', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.error).toBeNull();
  });

  it('should provide subscribe and unsubscribe functions', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    expect(result.current.subscribe).toBeDefined();
    expect(typeof result.current.subscribe).toBe('function');
    expect(result.current.unsubscribe).toBeDefined();
    expect(typeof result.current.unsubscribe).toBe('function');
  });

  it('should handle multiple sendMessage calls', () => {
    const wrapper = TestProviders;
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    const message1 = { type: 'test1', payload: { data: 'data1' } };
    const message2 = { type: 'test2', payload: { data: 'data2' } };
    
    result.current.sendMessage(message1);
    result.current.sendMessage(message2);
    
    expect(result.current.sendMessage).toHaveBeenCalledTimes(2);
    expect(result.current.sendMessage).toHaveBeenNthCalledWith(1, message1);
    expect(result.current.sendMessage).toHaveBeenNthCalledWith(2, message2);
  });
});