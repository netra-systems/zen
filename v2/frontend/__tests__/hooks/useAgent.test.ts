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

import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgent } from '@/hooks/useAgent';

// Mock fetch globally
global.fetch = jest.fn();

describe('useAgent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useAgent());
    
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should send message successfully', async () => {
    const mockResponse = {
      id: 'msg_123',
      content: 'Agent response',
      role: 'assistant',
      timestamp: new Date().toISOString()
    };
    
    (global.fetch as jest.Mock).mockImplementationOnce(async () => ({
      ok: true,
      json: async () => mockResponse,
    }));
    
    const { result } = renderHook(() => useAgent());
    
    await act(async () => {
      await result.current.sendMessage('Test message');
    });
    
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2); // User message + agent response
      expect(result.current.messages[0].content).toBe('Test message');
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[1].content).toBe('Agent response');
      expect(result.current.messages[1].role).toBe('assistant');
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  it('should handle API error', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(async () => ({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    }));
    
    const { result } = renderHook(() => useAgent());
    
    await act(async () => {
      await result.current.sendMessage('Test message');
    });
    
    await waitFor(() => {
      expect(result.current.error).toBe('Failed to send message');
      expect(result.current.isLoading).toBe(false);
      expect(result.current.messages).toHaveLength(1); // Only user message
    });
  });

  it('should handle network error', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    const { result } = renderHook(() => useAgent());
    
    await act(async () => {
      await result.current.sendMessage('Test message');
    });
    
    await waitFor(() => {
      expect(result.current.error).toBe('Failed to send message');
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should set loading state during message send', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    
    (global.fetch as jest.Mock).mockImplementationOnce(() => promise);
    
    const { result } = renderHook(() => useAgent());
    
    // Start sending message
    act(() => {
      result.current.sendMessage('Test message');
    });
    
    // Check loading state is true
    expect(result.current.isLoading).toBe(true);
    
    // Resolve the promise
    act(() => {
      resolvePromise!({
        ok: true,
        json: async () => ({ content: 'Response', role: 'assistant' }),
      });
    });
    
    // Wait for loading to complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should clear messages', () => {
    const { result } = renderHook(() => useAgent());
    
    // Add some messages first
    act(() => {
      result.current.messages = [
        { id: '1', content: 'Message 1', role: 'user', timestamp: new Date().toISOString() },
        { id: '2', content: 'Message 2', role: 'assistant', timestamp: new Date().toISOString() },
      ];
    });
    
    expect(result.current.messages).toHaveLength(2);
    
    // Clear messages
    act(() => {
      result.current.clearMessages();
    });
    
    expect(result.current.messages).toEqual([]);
  });

  it('should handle empty message', async () => {
    const { result } = renderHook(() => useAgent());
    
    await act(async () => {
      await result.current.sendMessage('');
    });
    
    // Should not make API call for empty message
    expect(global.fetch).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });

  it('should handle whitespace-only message', async () => {
    const { result } = renderHook(() => useAgent());
    
    await act(async () => {
      await result.current.sendMessage('   ');
    });
    
    // Should not make API call for whitespace-only message
    expect(global.fetch).not.toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });

  it('should maintain message history', async () => {
    const responses = [
      { id: 'resp1', content: 'First response', role: 'assistant' },
      { id: 'resp2', content: 'Second response', role: 'assistant' },
    ];
    
    (global.fetch as jest.Mock)
      .mockImplementationOnce(async () => ({
        ok: true,
        json: async () => responses[0],
      }))
      .mockImplementationOnce(async () => ({
        ok: true,
        json: async () => responses[1],
      }));
    
    const { result } = renderHook(() => useAgent());
    
    // Send first message
    await act(async () => {
      await result.current.sendMessage('First message');
    });
    
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });
    
    // Send second message
    await act(async () => {
      await result.current.sendMessage('Second message');
    });
    
    await waitFor(() => {
      expect(result.current.messages).toHaveLength(4);
      expect(result.current.messages[0].content).toBe('First message');
      expect(result.current.messages[1].content).toBe('First response');
      expect(result.current.messages[2].content).toBe('Second message');
      expect(result.current.messages[3].content).toBe('Second response');
    });
  });

  it('should handle concurrent messages', async () => {
    const mockResponse = {
      content: 'Response',
      role: 'assistant',
    };
    
    (global.fetch as jest.Mock).mockImplementation(async () => ({
      ok: true,
      json: async () => mockResponse,
    }));
    
    const { result } = renderHook(() => useAgent());
    
    // Send multiple messages concurrently
    await act(async () => {
      await Promise.all([
        result.current.sendMessage('Message 1'),
        result.current.sendMessage('Message 2'),
        result.current.sendMessage('Message 3'),
      ]);
    });
    
    // All messages should be processed
    expect(global.fetch).toHaveBeenCalledTimes(3);
  });

  it('should reset error on successful message', async () => {
    const { result } = renderHook(() => useAgent());
    
    // Set an error first
    act(() => {
      result.current.error = 'Previous error';
    });
    
    expect(result.current.error).toBe('Previous error');
    
    // Send successful message
    (global.fetch as jest.Mock).mockImplementationOnce(async () => ({
      ok: true,
      json: async () => ({ content: 'Success', role: 'assistant' }),
    }));
    
    await act(async () => {
      await result.current.sendMessage('New message');
    });
    
    await waitFor(() => {
      expect(result.current.error).toBeNull();
    });
  });
});