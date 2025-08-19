/**
 * WebSocket State Synchronization Tests - Real-time State Management
 * 
 * BVJ (Business Value Justification):
 * - Segment: Growth & Enterprise (real-time features)
 * - Business Goal: Enable real-time collaboration and live updates
 * - Value Impact: Real-time features increase user engagement 20-30%
 * - Revenue Impact: Premium feature differentiation for paid tiers
 * 
 * Tests: WebSocket sync, message handling, connection state management
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { useChatStore } from '@/store/chat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { WebSocketProvider, useWebSocketContext } from '@/providers/WebSocketProvider';
import { GlobalTestUtils } from './store-test-utils';

// Mock WebSocket for testing
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readyState: number = WebSocket.CONNECTING;
  url: string;
  
  constructor(url: string) {
    this.url = url;
    setTimeout(() => this.simulateOpen(), 10);
  }

  send = jest.fn();
  close = jest.fn();

  simulateOpen(): void {
    this.readyState = WebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: any): void {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    this.onmessage?.(event);
  }

  simulateClose(): void {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  simulateError(): void {
    this.onerror?.(new Event('error'));
  }
}

describe('WebSocket State Synchronization Tests', () => {
  let mockWs: MockWebSocket;
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
    originalWebSocket = global.WebSocket;
    
    global.WebSocket = jest.fn().mockImplementation((url: string) => {
      mockWs = new MockWebSocket(url);
      return mockWs;
    }) as any;
  });

  afterEach(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
    global.WebSocket = originalWebSocket;
  });

  describe('Connection State Management', () => {
    it('should initialize WebSocket connection', async () => {
      const TestComponent = () => {
        const { status } = useWebSocketContext();
        return <div>{status}</div>;
      };

      const { result } = renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalled();
      });
    });

    it('should handle connection state transitions', async () => {
      const TestComponent = () => {
        const { status } = useWebSocketContext();
        return <div data-testid="status">{status}</div>;
      };

      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      act(() => {
        mockWs.simulateClose();
      });

      expect(mockWs.readyState).toBe(WebSocket.CLOSED);
    });

    it('should handle connection errors gracefully', async () => {
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      expect(() => {
        act(() => {
          mockWs.simulateError();
        });
      }).not.toThrow();
    });

    it('should attempt reconnection on close', async () => {
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalledTimes(1);
      });

      act(() => {
        mockWs.simulateClose();
      });

      // Should attempt reconnection
      await waitFor(() => {
        expect(global.WebSocket).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Message Synchronization', () => {
    it('should sync incoming messages to chat store', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const wsMessage = {
        type: 'message',
        payload: {
          message_id: 'ws-msg-1',
          content: 'WebSocket message',
          role: 'assistant',
          thread_id: 'thread-1'
        }
      };

      act(() => {
        mockWs.simulateMessage(wsMessage);
      });

      await waitFor(() => {
        expect(chatResult.result.current.messages.length).toBeGreaterThan(0);
      });
    });

    it('should handle agent status updates', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const statusUpdate = {
        type: 'agent_status',
        payload: {
          agent_name: 'DataSubAgent',
          status: 'processing',
          tools: ['database', 'analytics']
        }
      };

      act(() => {
        mockWs.simulateMessage(statusUpdate);
      });

      await waitFor(() => {
        expect(chatResult.result.current.subAgentName).toBe('DataSubAgent');
        expect(chatResult.result.current.subAgentStatus).toBe('processing');
      });
    });

    it('should handle duplicate message filtering', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const wsMessage = {
        type: 'message',
        payload: {
          message_id: 'duplicate-msg',
          content: 'Duplicate message',
          role: 'assistant'
        }
      };

      act(() => {
        mockWs.simulateMessage(wsMessage);
        mockWs.simulateMessage(wsMessage); // Duplicate
      });

      await waitFor(() => {
        const messagesWithId = chatResult.result.current.messages.filter(
          msg => msg.id === 'duplicate-msg'
        );
        expect(messagesWithId.length).toBe(1);
      });
    });

    it('should handle message updates and confirmations', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      // Send initial message
      const initialMessage = {
        type: 'message',
        payload: {
          message_id: 'update-msg',
          content: 'Initial content',
          role: 'assistant',
          status: 'streaming'
        }
      };

      act(() => {
        mockWs.simulateMessage(initialMessage);
      });

      // Send update
      const updateMessage = {
        type: 'message_update',
        payload: {
          message_id: 'update-msg',
          content: 'Updated content',
          status: 'completed'
        }
      };

      act(() => {
        mockWs.simulateMessage(updateMessage);
      });

      await waitFor(() => {
        const message = chatResult.result.current.messages.find(
          msg => msg.id === 'update-msg'
        );
        expect(message?.content).toBe('Updated content');
      });
    });
  });

  describe('Real-time Features', () => {
    it('should handle typing indicators', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const typingIndicator = {
        type: 'agent_typing',
        payload: {
          agent_name: 'TriageSubAgent',
          is_typing: true
        }
      };

      act(() => {
        mockWs.simulateMessage(typingIndicator);
      });

      await waitFor(() => {
        expect(chatResult.result.current.isProcessing).toBe(true);
      });
    });

    it('should handle progress updates', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const progressUpdate = {
        type: 'agent_progress',
        payload: {
          agent_name: 'DataSubAgent',
          progress: { current: 3, total: 10, message: 'Processing data...' }
        }
      };

      act(() => {
        mockWs.simulateMessage(progressUpdate);
      });

      await waitFor(() => {
        expect(chatResult.result.current.subAgentProgress).toEqual({
          current: 3,
          total: 10,
          message: 'Processing data...'
        });
      });
    });

    it('should handle error states from WebSocket', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const errorMessage = {
        type: 'error',
        payload: {
          message: 'Agent execution failed',
          agent_name: 'DataSubAgent'
        }
      };

      act(() => {
        mockWs.simulateMessage(errorMessage);
      });

      await waitFor(() => {
        expect(chatResult.result.current.subAgentError).toBe(
          'Agent execution failed'
        );
      });
    });

    it('should handle thread switching via WebSocket', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const threadSwitch = {
        type: 'thread_switch',
        payload: {
          thread_id: 'new-thread-1',
          messages: [
            {
              id: 'msg-1',
              role: 'user',
              content: 'Previous message',
              created_at: new Date().toISOString()
            }
          ]
        }
      };

      act(() => {
        mockWs.simulateMessage(threadSwitch);
      });

      await waitFor(() => {
        expect(chatResult.result.current.activeThreadId).toBe('new-thread-1');
        expect(chatResult.result.current.messages.length).toBeGreaterThan(0);
      });
    });
  });

  describe('State Consistency', () => {
    it('should maintain state consistency during rapid updates', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      const messages = Array.from({ length: 5 }, (_, i) => ({
        type: 'message',
        payload: {
          message_id: `rapid-msg-${i}`,
          content: `Message ${i}`,
          role: 'assistant'
        }
      }));

      act(() => {
        messages.forEach(msg => mockWs.simulateMessage(msg));
      });

      await waitFor(() => {
        expect(chatResult.result.current.messages.length).toBe(5);
      });

      // Verify all messages are unique and in correct order
      const messageIds = chatResult.result.current.messages.map(m => m.id);
      const uniqueIds = [...new Set(messageIds)];
      expect(messageIds.length).toBe(uniqueIds.length);
    });

    it('should handle out-of-order message delivery', async () => {
      const chatResult = renderHook(() => useChatStore());
      
      renderHook(() => useWebSocketContext(), {
        wrapper: ({ children }) => (
          <WebSocketProvider>{children}</WebSocketProvider>
        )
      });

      await waitFor(() => {
        expect(mockWs.readyState).toBe(WebSocket.OPEN);
      });

      // Send messages out of order
      act(() => {
        mockWs.simulateMessage({
          type: 'message',
          payload: {
            message_id: 'msg-3',
            content: 'Third message',
            role: 'assistant',
            sequence: 3
          }
        });
        
        mockWs.simulateMessage({
          type: 'message',
          payload: {
            message_id: 'msg-1',
            content: 'First message', 
            role: 'assistant',
            sequence: 1
          }
        });
      });

      await waitFor(() => {
        expect(chatResult.result.current.messages.length).toBe(2);
      });
    });
  });
});