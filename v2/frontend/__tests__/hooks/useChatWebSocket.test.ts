/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-10T14:33:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for useChatWebSocket hook
 * Git: v6 | 88345b5 | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-improvement | Seq: 4
 * Review: Pending | Score: 85/100
 * ================================
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import WS from 'jest-websocket-mock';

// Mock stores
jest.mock('@/store/chat');
jest.mock('@/store/threadStore');
jest.mock('@/store/authStore');

describe('useChatWebSocket', () => {
  let server: WS;
  const mockUrl = 'ws://localhost:8000/ws';
  
  const mockChatStore = {
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    setSubAgentStatus: jest.fn(),
    setToolOutput: jest.fn(),
    setFinalReport: jest.fn(),
    clearMessages: jest.fn(),
    updateLastMessage: jest.fn(),
  };
  
  const mockThreadStore = {
    currentThread: { id: 'thread_123' },
    setCurrentThread: jest.fn(),
    updateThread: jest.fn(),
  };
  
  const mockAuthStore = {
    isAuthenticated: true,
    token: 'test_token_123',
    user: { id: 'user_123' },
  };

  beforeEach(async () => {
    jest.clearAllMocks();
    
    // Setup mock returns
    (useChatStore as unknown as jest.Mock).mockReturnValue(mockChatStore);
    (useThreadStore as unknown as jest.Mock).mockReturnValue(mockThreadStore);
    (useAuthStore as unknown as jest.Mock).mockReturnValue(mockAuthStore);
    
    // Create WebSocket server
    server = new WS(mockUrl);
  });

  afterEach(() => {
    WS.clean();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.reconnectAttempts).toBe(0);
    expect(typeof result.current.sendMessage).toBe('function');
    expect(typeof result.current.connect).toBe('function');
    expect(typeof result.current.disconnect).toBe('function');
  });

  it('should connect to WebSocket when authenticated', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });

  it('should not connect when not authenticated', () => {
    (useAuthStore as unknown as jest.Mock).mockReturnValue({
      ...mockAuthStore,
      isAuthenticated: false,
    });
    
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBe('User not authenticated');
  });

  it('should send messages when connected', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const message = {
      type: 'user_message',
      payload: { text: 'Hello', threadId: 'thread_123' },
    };
    
    act(() => {
      result.current.sendMessage(message);
    });
    
    await expect(server).toReceiveMessage(JSON.stringify(message));
  });

  it('should handle incoming messages', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const chatMessage = {
      type: 'chat_message',
      message: {
        id: 'msg_123',
        content: 'Response from agent',
        role: 'assistant',
      },
    };
    
    act(() => {
      server.send(JSON.stringify(chatMessage));
    });
    
    await waitFor(() => {
      expect(mockChatStore.addMessage).toHaveBeenCalledWith(chatMessage.message);
    });
  });

  it('should handle agent status updates', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const statusUpdate = {
      type: 'agent_status',
      data: {
        name: 'TestAgent',
        status: 'processing',
        lifecycle: 'running',
      },
    };
    
    act(() => {
      server.send(JSON.stringify(statusUpdate));
    });
    
    await waitFor(() => {
      expect(mockChatStore.setSubAgentStatus).toHaveBeenCalledWith(statusUpdate.data);
    });
  });

  it('should handle tool output messages', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const toolOutput = {
      type: 'tool_output',
      data: {
        tool: 'analyzer',
        output: 'Analysis complete',
      },
    };
    
    act(() => {
      server.send(JSON.stringify(toolOutput));
    });
    
    await waitFor(() => {
      expect(mockChatStore.setToolOutput).toHaveBeenCalledWith(toolOutput.data);
    });
  });

  it('should handle final report messages', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const finalReport = {
      type: 'final_report',
      report: {
        summary: 'Task completed successfully',
        details: 'All optimizations applied',
      },
    };
    
    act(() => {
      server.send(JSON.stringify(finalReport));
    });
    
    await waitFor(() => {
      expect(mockChatStore.setFinalReport).toHaveBeenCalledWith(finalReport.report);
      expect(mockChatStore.setProcessing).toHaveBeenCalledWith(false);
    });
  });

  it('should handle connection errors', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    act(() => {
      server.error();
    });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
      expect(result.current.error).toBeTruthy();
    });
  });

  it('should handle disconnection', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    act(() => {
      result.current.disconnect();
    });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });
  });

  it('should attempt reconnection on disconnect', async () => {
    jest.useFakeTimers();
    
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    // Simulate unexpected disconnect
    act(() => {
      server.close();
    });
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false);
    });
    
    // Fast-forward time to trigger reconnection
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    
    await waitFor(() => {
      expect(result.current.reconnectAttempts).toBeGreaterThan(0);
    });
    
    jest.useRealTimers();
  });

  it('should queue messages when disconnected', () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    const message = {
      type: 'user_message',
      payload: { text: 'Queued message' },
    };
    
    // Try to send without connecting
    act(() => {
      result.current.sendMessage(message);
    });
    
    // Message should be queued
    expect(result.current.messageQueue).toContainEqual(message);
  });

  it('should send queued messages on reconnection', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    const message = {
      type: 'user_message',
      payload: { text: 'Queued message' },
    };
    
    // Queue a message
    act(() => {
      result.current.sendMessage(message);
    });
    
    expect(result.current.messageQueue).toHaveLength(1);
    
    // Connect
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    // Queued message should be sent
    await expect(server).toReceiveMessage(JSON.stringify(message));
    
    await waitFor(() => {
      expect(result.current.messageQueue).toHaveLength(0);
    });
  });

  it('should handle heartbeat messages', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    // Send heartbeat
    act(() => {
      server.send(JSON.stringify({ type: 'heartbeat' }));
    });
    
    // Should respond with heartbeat
    await expect(server).toReceiveMessage(JSON.stringify({ type: 'heartbeat' }));
  });

  it('should update thread on thread update message', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const threadUpdate = {
      type: 'thread_update',
      thread: {
        id: 'thread_123',
        title: 'Updated Thread',
        updated_at: new Date().toISOString(),
      },
    };
    
    act(() => {
      server.send(JSON.stringify(threadUpdate));
    });
    
    await waitFor(() => {
      expect(mockThreadStore.updateThread).toHaveBeenCalledWith(threadUpdate.thread);
    });
  });

  it('should handle error messages', async () => {
    const { result } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    const errorMessage = {
      type: 'error',
      error: 'Something went wrong',
      details: 'Connection timeout',
    };
    
    act(() => {
      server.send(JSON.stringify(errorMessage));
    });
    
    await waitFor(() => {
      expect(result.current.error).toBe('Something went wrong: Connection timeout');
    });
  });

  it('should clean up on unmount', async () => {
    const { result, unmount } = renderHook(() => useChatWebSocket(mockUrl));
    
    act(() => {
      result.current.connect();
    });
    
    await server.connected;
    
    unmount();
    
    // WebSocket should be closed
    expect(server.readyState).toBe(WebSocket.CLOSED);
  });
});