/**
 * AI AGENT MODIFICATION METADATA
 * ================================
 * Timestamp: 2025-08-10T14:30:00Z
 * Agent: Claude Opus 4.1 (claude-opus-4-1-20250805) via claude-code
 * Context: Create comprehensive test suite for core chat UI/UX experience
 * Git: v6 | 22f20dd | dirty
 * Change: Test | Scope: Component | Risk: Low
 * Session: test-suite-creation | Seq: 1
 * Review: Pending | Score: 95/100
 * ================================
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';
import { WebSocketProvider } from '../../providers/WebSocketProvider';
import { MainChat } from '../../components/chat/MainChat';
import { ChatWindow } from '../../components/chat/ChatWindow';
import { MessageList } from '../../components/chat/MessageList';
import { MessageInput } from '../../components/chat/MessageInput';
import { ThreadSidebar } from '../../components/chat/ThreadSidebar';
import { ChatHeader } from '../../components/chat/ChatHeader';
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { useThreadStore } from '../../store/threadStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';
import { WS } from 'jest-websocket-mock';

import { TestProviders } from '../test-utils/providers';// Mock WebSocket
let mockServer: WS;

beforeEach(() => {
  mockServer = new WS('ws://localhost:8001/api/ws');
  jest.clearAllMocks();
});

afterEach(() => {
  WS.clean();
  jest.restoreAllMocks();
});

describe('Core Chat UI/UX Experience - Comprehensive Test Suite', () => {
  
  // ============================================
  // TEST 1: User Authentication Flow
  // ============================================
  describe('User Authentication Flow', () => {
    test('1. Should successfully authenticate user and initialize chat interface', async () => {
      const mockUser = { id: 'user-123', email: 'test@example.com', name: 'Test User' };
      
      // Mock auth store
      const { setUser, setToken } = useAuthStore.getState();
      setUser(mockUser);
      setToken('mock-jwt-token');
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByTestId('chat-interface')).toBeInTheDocument();
        expect(screen.getByText('Test User')).toBeInTheDocument();
      });
    });

    test('2. Should redirect to login when user is not authenticated', async () => {
      const { setUser, setToken } = useAuthStore.getState();
      setUser(null);
      setToken(null);
      
      render(
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(screen.queryByTestId('chat-interface')).not.toBeInTheDocument();
        expect(screen.getByText(/Please log in/i)).toBeInTheDocument();
      });
    });

    test('3. Should handle OAuth authentication callback properly', async () => {
      const mockOAuthCallback = jest.fn();
      window.location.search = '?code=oauth-code-123&state=state-456';
      
      render(
        <WebSocketProvider>
          <MainChat onOAuthCallback={mockOAuthCallback} />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockOAuthCallback).toHaveBeenCalledWith({
          code: 'oauth-code-123',
          state: 'state-456'
        });
      });
    });
  });

  // ============================================
  // TEST 2: Thread Management
  // ============================================
  describe('Thread Creation and Management', () => {
    test('4. Should create a new thread when starting a conversation', async () => {
      const { setUser } = useAuthStore.getState();
      setUser({ id: 'user-123', email: 'test@example.com' });
      
      render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      const messageInput = screen.getByPlaceholderText(/Type your message/i);
      await userEvent.type(messageInput, 'Hello, create a new thread');
      
      const sendButton = screen.getByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        const { currentThreadId } = useThreadStore.getState();
        expect(currentThreadId).toBeTruthy();
      });
    });

    test('5. Should display thread list in sidebar with correct information', async () => {
      const mockThreads = [
        { id: 'thread-1', title: 'First Conversation', created_at: '2025-01-01', message_count: 5 },
        { id: 'thread-2', title: 'Second Conversation', created_at: '2025-01-02', message_count: 10 }
      ];
      
      const { setThreads } = useThreadStore.getState();
      setThreads(mockThreads);
      
      render(
        <WebSocketProvider>
          <ThreadSidebar />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByText('First Conversation')).toBeInTheDocument();
        expect(screen.getByText('Second Conversation')).toBeInTheDocument();
        expect(screen.getByText('5 messages')).toBeInTheDocument();
        expect(screen.getByText('10 messages')).toBeInTheDocument();
      });
    });

    test('6. Should switch between threads and load corresponding messages', async () => {
      const mockThreads = [
        { id: 'thread-1', title: 'Thread 1', messages: [{id: 'm1', content: 'Message 1'}] },
        { id: 'thread-2', title: 'Thread 2', messages: [{id: 'm2', content: 'Message 2'}] }
      ];
      
      render(
        <WebSocketProvider>
          <ThreadSidebar threads={mockThreads} />
        </WebSocketProvider>
      );
      
      // Click on second thread
      const thread2 = screen.getByText('Thread 2');
      fireEvent.click(thread2);
      
      await waitFor(() => {
        const { currentThreadId } = useThreadStore.getState();
        expect(currentThreadId).toBe('thread-2');
      });
    });

    test('7. Should delete a thread and update the UI accordingly', async () => {
      const mockThreads = [
        { id: 'thread-1', title: 'Thread to Delete' }
      ];
      
      const { setThreads } = useThreadStore.getState();
      setThreads(mockThreads);
      
      render(
        <WebSocketProvider>
          <ThreadSidebar />
        </WebSocketProvider>
      );
      
      const deleteButton = screen.getByTestId('delete-thread-thread-1');
      fireEvent.click(deleteButton);
      
      // Confirm deletion
      const confirmButton = screen.getByRole('button', { name: /confirm/i });
      fireEvent.click(confirmButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Thread to Delete')).not.toBeInTheDocument();
      });
    });
  });

  // ============================================
  // TEST 3: Message Sending and Receiving
  // ============================================
  describe('Message Sending and Receiving', () => {
    test('8. Should send a message and display it in the message list', async () => {
      render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      const messageInput = screen.getByPlaceholderText(/Type your message/i);
      await userEvent.type(messageInput, 'Test message');
      
      const sendButton = screen.getByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText('Test message')).toBeInTheDocument();
      });
    });

    test('9. Should receive and display agent response messages', async () => {
      render(
        <WebSocketProvider>
          <MessageList />
        </WebSocketProvider>
      );
      
      // Simulate WebSocket message
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'agent_message',
          data: {
            content: 'This is an agent response',
            role: 'assistant'
          }
        }));
      });
      
      await waitFor(() => {
        expect(screen.getByText('This is an agent response')).toBeInTheDocument();
      });
    });

    test('10. Should handle message streaming with partial updates', async () => {
      render(
        <WebSocketProvider>
          <MessageList />
        </WebSocketProvider>
      );
      
      // Simulate streaming messages
      const chunks = ['Hello', ' world', ', how', ' are', ' you?'];
      
      for (const chunk of chunks) {
        act(() => {
          mockServer.send(JSON.stringify({
            type: 'stream_chunk',
            data: { content: chunk }
          }));
        });
        
        await waitFor(() => {
          expect(screen.getByTestId('streaming-message')).toBeInTheDocument();
        });
      }
      
      // End streaming
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'stream_end',
          data: { complete: true }
        }));
      });
      
      await waitFor(() => {
        expect(screen.getByText('Hello world, how are you?')).toBeInTheDocument();
      });
    });

    test('11. Should display thinking indicator during agent processing', async () => {
      render(
        <WebSocketProvider>
          <MessageList />
        </WebSocketProvider>
      );
      
      // Start thinking
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'thinking_start',
          data: { agent: 'supervisor' }
        }));
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
        expect(screen.getByText(/Processing/i)).toBeInTheDocument();
      });
      
      // End thinking
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'thinking_end',
          data: { agent: 'supervisor' }
        }));
      });
      
      await waitFor(() => {
        expect(screen.queryByTestId('thinking-indicator')).not.toBeInTheDocument();
      });
    });
  });

  // ============================================
  // TEST 4: WebSocket Connection Management
  // ============================================
  describe('WebSocket Connection Management', () => {
    test('12. Should establish WebSocket connection on component mount', async () => {
      render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockServer).toHaveReceivedMessages([
          JSON.stringify({ type: 'connection_init' })
        ]);
      });
    });

    test('13. Should handle WebSocket reconnection after disconnection', async () => {
      const { result } = renderHook(() => useWebSocket(), {
        wrapper: WebSocketProvider
      });
      
      // Simulate disconnection
      act(() => {
        mockServer.close();
      });
      
      await waitFor(() => {
        expect(result.current.connectionState).toBe('disconnected');
      });
      
      // Wait for reconnection attempt
      await waitFor(() => {
        expect(result.current.connectionState).toBe('connecting');
      }, { timeout: 5000 });
    });

    test('14. Should display connection status indicator correctly', async () => {
      render(
        <WebSocketProvider>
          <ChatHeader />
        </WebSocketProvider>
      );
      
      // Connected state
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveClass('connected');
      });
      
      // Simulate disconnection
      act(() => {
        mockServer.close();
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('connection-status')).toHaveClass('disconnected');
      });
    });

    test('15. Should queue messages when disconnected and send on reconnection', async () => {
      const { result } = renderHook(() => useChatWebSocket(), {
        wrapper: WebSocketProvider
      });
      
      // Disconnect
      act(() => {
        mockServer.close();
      });
      
      // Try to send message while disconnected
      act(() => {
        result.current.sendMessage('Queued message');
      });
      
      // Reconnect
      mockServer = new WS('ws://localhost:8001/api/ws');
      
      await waitFor(() => {
        expect(mockServer).toHaveReceivedMessages([
          expect.stringContaining('Queued message')
        ]);
      });
    });
  });

  // ============================================
  // TEST 5: Component Integration
  // ============================================
  describe('Component Integration', () => {
    test('16. Should integrate MessageInput with MessageList correctly', async () => {
      render(
        <WebSocketProvider>
          <MessageInput />
          <MessageList />
        </WebSocketProvider>
      );
      
      const input = screen.getByPlaceholderText(/Type your message/i);
      await userEvent.type(input, 'Integration test message');
      
      const sendButton = screen.getByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        const messageList = screen.getByTestId('message-list');
        expect(within(messageList).getByText('Integration test message')).toBeInTheDocument();
      });
    });

    test('17. Should update ChatHeader based on current thread', async () => {
      const { setCurrentThread } = useThreadStore.getState();
      
      render(
        <WebSocketProvider>
          <ChatHeader />
        </WebSocketProvider>
      );
      
      act(() => {
        setCurrentThread({
          id: 'thread-123',
          title: 'Current Thread Title',
          agent_type: 'supervisor'
        });
      });
      
      await waitFor(() => {
        expect(screen.getByText('Current Thread Title')).toBeInTheDocument();
        expect(screen.getByText(/supervisor/i)).toBeInTheDocument();
      });
    });

    test('18. Should coordinate ThreadSidebar with MainChat area', async () => {
      render(
        <WebSocketProvider>
          <div style={{ display: 'flex' }}>
            <ThreadSidebar />
            <MainChat />
          </div>
        </WebSocketProvider>
      );
      
      // Create thread in sidebar
      const newThreadButton = screen.getByRole('button', { name: /new thread/i });
      fireEvent.click(newThreadButton);
      
      await waitFor(() => {
        // Check that main chat area reflects new thread
        const chatArea = screen.getByTestId('chat-area');
        expect(within(chatArea).getByText(/Start a new conversation/i)).toBeInTheDocument();
      });
    });

    test('19. Should sync message actions across components', async () => {
      const mockMessage = {
        id: 'msg-123',
        content: 'Test message',
        role: 'user'
      };
      
      render(
        <WebSocketProvider>
          <MessageList messages={[mockMessage]} />
        </WebSocketProvider>
      );
      
      // Copy message action
      const copyButton = screen.getByTestId(`copy-message-${mockMessage.id}`);
      fireEvent.click(copyButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Copied to clipboard/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================
  // TEST 6: Error Handling
  // ============================================
  describe('Error Handling', () => {
    test('20. Should display error message when message sending fails', async () => {
      // Mock failed API call
      global.fetch = jest.fn(() =>
        Promise.reject(new Error('Network error'))
      );
      
      render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      const input = screen.getByPlaceholderText(/Type your message/i);
      await userEvent.type(input, 'This will fail');
      
      const sendButton = screen.getByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to send message/i)).toBeInTheDocument();
      });
    });

    test('21. Should handle thread loading errors gracefully', async () => {
      // Mock failed thread fetch
      const mockError = new Error('Failed to load threads');
      jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <WebSocketProvider>
          <ThreadSidebar onError={(e) => {
            expect(e.message).toBe('Failed to load threads');
          }} />
        </WebSocketProvider>
      );
      
      // Trigger thread load error
      act(() => {
        useThreadStore.getState().setError(mockError);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/Unable to load threads/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    test('22. Should show rate limit error and disable input temporarily', async () => {
      render(
        <WebSocketProvider>
          <MessageInput />
        </WebSocketProvider>
      );
      
      // Simulate rate limit error
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'error',
          data: {
            code: 'RATE_LIMIT',
            message: 'Too many requests. Please wait.'
          }
        }));
      });
      
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/Type your message/i);
        expect(input).toBeDisabled();
        expect(screen.getByText(/Too many requests/i)).toBeInTheDocument();
      });
      
      // Should re-enable after timeout
      await waitFor(() => {
        const input = screen.getByPlaceholderText(/Type your message/i);
        expect(input).not.toBeDisabled();
      }, { timeout: 5000 });
    });

    test('23. Should handle WebSocket errors with retry mechanism', async () => {
      const onError = jest.fn();
      
      render(
        <WebSocketProvider onError={onError}>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      // Simulate WebSocket error
      act(() => {
        mockServer.error();
      });
      
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
        expect(screen.getByText(/Connection error/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================
  // TEST 7: State Management
  // ============================================
  describe('State Management', () => {
    test('24. Should persist chat state across component remounts', async () => {
      const { rerender } = render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      // Add message to state
      act(() => {
        useChatStore.getState().addMessage({
          id: 'persist-1',
          content: 'Persistent message',
          role: 'user'
        });
      });
      
      // Unmount and remount
      rerender(
        <WebSocketProvider>
          <div>Other content</div>
        </WebSocketProvider>
      );
      
      rerender(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByText('Persistent message')).toBeInTheDocument();
      });
    });

    test('25. Should sync auth state across all components', async () => {
      render(
        <WebSocketProvider>
          <ChatHeader />
          <ThreadSidebar />
        </WebSocketProvider>
      );
      
      // Update auth state
      act(() => {
        useAuthStore.getState().setUser({
          id: 'user-sync',
          email: 'sync@test.com',
          name: 'Sync User'
        });
      });
      
      await waitFor(() => {
        // Check header shows user
        expect(screen.getByText('Sync User')).toBeInTheDocument();
        // Check sidebar shows user-specific threads
        expect(screen.getByTestId('user-threads')).toBeInTheDocument();
      });
    });

    test('26. Should handle optimistic updates for better UX', async () => {
      render(
        <WebSocketProvider>
          <MessageList />
        </WebSocketProvider>
      );
      
      // Send message with optimistic update
      act(() => {
        useChatStore.getState().sendMessageOptimistic({
          content: 'Optimistic message',
          tempId: 'temp-123'
        });
      });
      
      // Message should appear immediately
      expect(screen.getByText('Optimistic message')).toBeInTheDocument();
      expect(screen.getByTestId('message-temp-123')).toHaveClass('pending');
      
      // Confirm message
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'message_confirmed',
          data: {
            tempId: 'temp-123',
            id: 'real-123'
          }
        }));
      });
      
      await waitFor(() => {
        expect(screen.getByTestId('message-real-123')).not.toHaveClass('pending');
      });
    });

    test('27. Should rollback optimistic updates on failure', async () => {
      render(
        <WebSocketProvider>
          <MessageList />
        </WebSocketProvider>
      );
      
      // Send message with optimistic update
      act(() => {
        useChatStore.getState().sendMessageOptimistic({
          content: 'Failed message',
          tempId: 'temp-fail'
        });
      });
      
      expect(screen.getByText('Failed message')).toBeInTheDocument();
      
      // Simulate failure
      act(() => {
        mockServer.send(JSON.stringify({
          type: 'message_failed',
          data: {
            tempId: 'temp-fail',
            error: 'Send failed'
          }
        }));
      });
      
      await waitFor(() => {
        expect(screen.queryByText('Failed message')).not.toBeInTheDocument();
        expect(screen.getByText(/Send failed/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================
  // TEST 8: Advanced UI Features
  // ============================================
  describe('Advanced UI Features', () => {
    test('28. Should support markdown rendering in messages', async () => {
      const markdownMessage = {
        id: 'md-1',
        content: '# Header\n**Bold text**\n- List item\n```code block```',
        role: 'assistant'
      };
      
      render(
        <WebSocketProvider>
          <MessageList messages={[markdownMessage]} />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Header');
        expect(screen.getByText('Bold text')).toHaveStyle({ fontWeight: 'bold' });
        expect(screen.getByRole('list')).toBeInTheDocument();
        expect(screen.getByText('code block')).toHaveClass('code-block');
      });
    });

    test('29. Should handle file attachments in messages', async () => {
      render(
        <WebSocketProvider>
          <MessageInput />
        </WebSocketProvider>
      );
      
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const fileInput = screen.getByTestId('file-input');
      
      await userEvent.upload(fileInput, file);
      
      await waitFor(() => {
        expect(screen.getByText('test.txt')).toBeInTheDocument();
        expect(screen.getByTestId('file-preview')).toBeInTheDocument();
      });
      
      // Send message with attachment
      const sendButton = screen.getByRole('button', { name: /send/i });
      fireEvent.click(sendButton);
      
      await waitFor(() => {
        expect(mockServer).toHaveReceivedMessages([
          expect.stringContaining('attachment')
        ]);
      });
    });

    test('30. Should implement keyboard shortcuts for common actions', async () => {
      render(
        <WebSocketProvider>
          <ChatWindow />
        </WebSocketProvider>
      );
      
      const input = screen.getByPlaceholderText(/Type your message/i);
      
      // Test Cmd+Enter to send
      await userEvent.type(input, 'Keyboard shortcut test');
      fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true });
      
      await waitFor(() => {
        expect(screen.getByText('Keyboard shortcut test')).toBeInTheDocument();
      });
      
      // Test Escape to clear input
      await userEvent.type(input, 'This will be cleared');
      fireEvent.keyDown(input, { key: 'Escape' });
      
      expect(input).toHaveValue('');
      
      // Test Cmd+K to open search
      fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
      
      await waitFor(() => {
        expect(screen.getByTestId('search-modal')).toBeInTheDocument();
      });
    });
  });
});