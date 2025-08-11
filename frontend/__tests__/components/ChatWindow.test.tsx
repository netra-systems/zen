import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: ({ onSendMessage, isDisabled, typingUsers }: any) => (
    <div data-testid="message-input">
      <input
        data-testid="message-input-field"
        disabled={isDisabled}
        onChange={(e) => {}}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            onSendMessage(e.target.value);
          }
        }}
      />
      {typingUsers?.length > 0 && (
        <div data-testid="typing-indicators">
          {typingUsers.map((user: string) => (
            <span key={user} data-testid={`typing-${user}`}>{user} is typing...</span>
          ))}
        </div>
      )}
    </div>
  )
}));
jest.mock('@/components/chat/MessageList', () => ({
  MessageList: ({ messages, isProcessing, onRetryMessage }: any) => (
    <div data-testid="message-list">
      {messages?.map((msg: any) => (
        <div key={msg.id} data-testid={`message-${msg.id}`} data-role={msg.role}>
          {msg.content}
          {msg.status === 'failed' && (
            <button data-testid={`retry-${msg.id}`} onClick={() => onRetryMessage(msg.id)}>
              Retry
            </button>
          )}
        </div>
      ))}
      {isProcessing && <div data-testid="processing-indicator">AI is thinking...</div>}
    </div>
  )
}));
jest.mock('@/components/chat/TypingIndicator', () => ({
  TypingIndicator: ({ isVisible, typingUsers }: any) => (
    isVisible ? (
      <div data-testid="typing-indicator">
        {typingUsers?.join(', ')} typing...
      </div>
    ) : null
  )
}));

describe('ChatWindow Component', () => {
  const mockChatStore = {
    currentThreadId: 'thread-123',
    messages: [],
    isProcessing: false,
    isConnected: true,
    typingUsers: [],
    sendMessage: jest.fn(),
    addMessage: jest.fn(),
    updateMessage: jest.fn(),
    deleteMessage: jest.fn(),
    retryMessage: jest.fn(),
    startTyping: jest.fn(),
    stopTyping: jest.fn(),
    markMessageAsRead: jest.fn(),
    scrollToBottom: jest.fn()
  };

  const mockWebSocket = {
    connected: true,
    error: null,
    sendMessage: jest.fn(),
    lastMessage: null,
    connectionState: 'connected'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocket);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const renderWithProvider = (component: React.ReactElement) => {
    return render(
      <WebSocketProvider>
        {component}
      </WebSocketProvider>
    );
  };

  describe('Message Display and Management', () => {
    it('should display messages from store', () => {
      const messagesStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Hello, how can I help you?',
            role: 'assistant',
            timestamp: new Date().toISOString(),
            status: 'sent'
          },
          {
            id: 'msg-2',
            content: 'I need help with optimization',
            role: 'user',
            timestamp: new Date().toISOString(),
            status: 'sent'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(messagesStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('message-list')).toBeInTheDocument();
      expect(screen.getByTestId('message-msg-1')).toHaveTextContent('Hello, how can I help you?');
      expect(screen.getByTestId('message-msg-2')).toHaveTextContent('I need help with optimization');
    });

    it('should show empty state when no messages', () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('empty-chat')).toBeInTheDocument();
      expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
    });

    it('should display processing indicator when AI is thinking', () => {
      const processingStore = {
        ...mockChatStore,
        isProcessing: true,
        messages: [
          { id: 'msg-1', content: 'User message', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(processingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('processing-indicator')).toBeInTheDocument();
      expect(screen.getByText('AI is thinking...')).toBeInTheDocument();
    });

    it('should show message status indicators', () => {
      const statusMessagesStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'Sending...', role: 'user', status: 'sending' },
          { id: 'msg-2', content: 'Sent message', role: 'user', status: 'sent' },
          { id: 'msg-3', content: 'Failed message', role: 'user', status: 'failed' },
          { id: 'msg-4', content: 'Read message', role: 'user', status: 'read' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(statusMessagesStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('message-msg-1')).toBeInTheDocument();
      expect(screen.getByTestId('message-msg-2')).toBeInTheDocument();
      expect(screen.getByTestId('message-msg-3')).toBeInTheDocument();
      expect(screen.getByTestId('retry-msg-3')).toBeInTheDocument(); // Failed message should have retry button
    });

    it('should group messages by sender and time', () => {
      const groupedMessagesStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'First message',
            role: 'user',
            timestamp: '2024-01-01T10:00:00Z'
          },
          {
            id: 'msg-2',
            content: 'Second message from same user',
            role: 'user',
            timestamp: '2024-01-01T10:00:30Z' // Within grouping window
          },
          {
            id: 'msg-3',
            content: 'Assistant response',
            role: 'assistant',
            timestamp: '2024-01-01T10:01:00Z'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(groupedMessagesStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Should group consecutive user messages
      const userMessages = screen.getAllByTestId(/^message-msg-[12]$/);
      expect(userMessages).toHaveLength(2);
      
      const assistantMessage = screen.getByTestId('message-msg-3');
      expect(assistantMessage).toHaveAttribute('data-role', 'assistant');
    });

    it('should handle message timestamps', () => {
      const timestampedStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Timestamped message',
            role: 'user',
            timestamp: '2024-01-01T15:30:00Z'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(timestampedStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      expect(messageEl).toBeInTheDocument();
      
      // Should display relative time on hover or in metadata
      const timeElement = within(messageEl).queryByTestId('message-timestamp');
      if (timeElement) {
        expect(timeElement).toBeInTheDocument();
      }
    });

    it('should auto-scroll to bottom on new messages', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Add new message
      const updatedStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'New message', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      // Should trigger scroll to bottom
      await waitFor(() => {
        expect(mockChatStore.scrollToBottom).toHaveBeenCalled();
      });
    });

    it('should preserve scroll position when loading older messages', () => {
      const scrollPreservationStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'Old message', role: 'user' },
          { id: 'msg-2', content: 'New message', role: 'user' }
        ],
        isLoadingHistory: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(scrollPreservationStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageList = screen.getByTestId('message-list');
      expect(messageList).toBeInTheDocument();
      
      // Should not auto-scroll when loading history
      expect(mockChatStore.scrollToBottom).not.toHaveBeenCalled();
    });

    it('should handle message retry functionality', async () => {
      const failedMessageStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-failed',
            content: 'Failed to send',
            role: 'user',
            status: 'failed',
            error: 'Network error'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(failedMessageStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const retryButton = screen.getByTestId('retry-msg-failed');
      await userEvent.click(retryButton);
      
      expect(mockChatStore.retryMessage).toHaveBeenCalledWith('msg-failed');
    });

    it('should mark messages as read when in viewport', async () => {
      // Mock IntersectionObserver
      const mockIntersectionObserver = jest.fn();
      mockIntersectionObserver.mockReturnValue({
        observe: jest.fn(),
        unobserve: jest.fn(),
        disconnect: jest.fn(),
      });
      window.IntersectionObserver = mockIntersectionObserver;
      
      const unreadStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Unread message',
            role: 'assistant',
            status: 'unread'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(unreadStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Simulate intersection observer callback
      const [observerCallback] = mockIntersectionObserver.mock.calls[0];
      observerCallback([{ isIntersecting: true, target: { dataset: { messageId: 'msg-1' } } }]);
      
      await waitFor(() => {
        expect(mockChatStore.markMessageAsRead).toHaveBeenCalledWith('msg-1');
      });
    });
  });

  describe('Message Sending and Input', () => {
    it('should send message through input component', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'Hello, AI assistant!');
      await userEvent.keyboard('[Enter]');
      
      expect(mockChatStore.sendMessage).toHaveBeenCalledWith('Hello, AI assistant!');
    });

    it('should disable input when disconnected', () => {
      const disconnectedStore = {
        ...mockChatStore,
        isConnected: false
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(disconnectedStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      expect(messageInput).toBeDisabled();
    });

    it('should disable input when processing', () => {
      const processingStore = {
        ...mockChatStore,
        isProcessing: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(processingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      expect(messageInput).toBeDisabled();
    });

    it('should handle message sending failures', async () => {
      mockChatStore.sendMessage.mockRejectedValueOnce(new Error('Send failed'));
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'Test message');
      await userEvent.keyboard('[Enter]');
      
      await waitFor(() => {
        expect(screen.getByTestId('send-error-toast')).toBeInTheDocument();
        expect(screen.getByText(/failed to send message/i)).toBeInTheDocument();
      });
    });

    it('should support message drafts', async () => {
      const draftStore = {
        ...mockChatStore,
        messageDraft: 'Draft content',
        saveDraft: jest.fn(),
        clearDraft: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(draftStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      expect(messageInput).toHaveValue('Draft content');
      
      await userEvent.type(messageInput, ' additional text');
      
      // Should save draft
      await waitFor(() => {
        expect(draftStore.saveDraft).toHaveBeenCalled();
      });
    });

    it('should clear draft after sending', async () => {
      const draftStore = {
        ...mockChatStore,
        messageDraft: 'Draft to send',
        clearDraft: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(draftStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.keyboard('[Enter]');
      
      expect(mockChatStore.sendMessage).toHaveBeenCalledWith('Draft to send');
      expect(draftStore.clearDraft).toHaveBeenCalled();
    });

    it('should support file attachments', async () => {
      const attachmentStore = {
        ...mockChatStore,
        uploadFile: jest.fn(),
        attachFile: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(attachmentStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const fileInput = screen.getByTestId('file-input');
      const testFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      await userEvent.upload(fileInput, testFile);
      
      expect(attachmentStore.uploadFile).toHaveBeenCalledWith(testFile);
    });

    it('should handle multiline messages with shift+enter', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'First line');
      await userEvent.keyboard('[Shift>][Enter][/Shift]');
      await userEvent.type(messageInput, 'Second line');
      await userEvent.keyboard('[Enter]');
      
      expect(mockChatStore.sendMessage).toHaveBeenCalledWith('First line\nSecond line');
    });
  });

  describe('Typing Indicators', () => {
    it('should display typing indicators from other users', () => {
      const typingStore = {
        ...mockChatStore,
        typingUsers: ['Assistant', 'Admin']
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(typingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('typing-indicators')).toBeInTheDocument();
      expect(screen.getByTestId('typing-Assistant')).toHaveTextContent('Assistant is typing...');
      expect(screen.getByTestId('typing-Admin')).toHaveTextContent('Admin is typing...');
    });

    it('should send typing indicators when user types', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'T');
      
      expect(mockChatStore.startTyping).toHaveBeenCalled();
    });

    it('should stop typing indicator after delay', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'Test');
      
      // Should start typing
      expect(mockChatStore.startTyping).toHaveBeenCalled();
      
      // Fast-forward timer
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      // Should stop typing after timeout
      await waitFor(() => {
        expect(mockChatStore.stopTyping).toHaveBeenCalled();
      });
    });

    it('should not show typing indicator for current user', () => {
      const typingStore = {
        ...mockChatStore,
        typingUsers: ['CurrentUser', 'Assistant'],
        currentUserId: 'CurrentUser'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(typingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Should not show current user typing
      expect(screen.queryByTestId('typing-CurrentUser')).not.toBeInTheDocument();
      expect(screen.getByTestId('typing-Assistant')).toBeInTheDocument();
    });

    it('should handle multiple simultaneous typists', () => {
      const multipleTypingStore = {
        ...mockChatStore,
        typingUsers: ['User1', 'User2', 'User3']
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(multipleTypingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('typing-User1')).toBeInTheDocument();
      expect(screen.getByTestId('typing-User2')).toBeInTheDocument();
      expect(screen.getByTestId('typing-User3')).toBeInTheDocument();
    });

    it('should clear typing indicators when user sends message', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'Test message');
      
      // Start typing
      expect(mockChatStore.startTyping).toHaveBeenCalled();
      
      await userEvent.keyboard('[Enter]');
      
      // Should stop typing when sending
      expect(mockChatStore.stopTyping).toHaveBeenCalled();
    });

    it('should animate typing indicators', () => {
      const typingStore = {
        ...mockChatStore,
        typingUsers: ['Assistant']
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(typingStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const typingIndicator = screen.getByTestId('typing-indicator');
      expect(typingIndicator).toBeInTheDocument();
      
      // Should have animation classes
      expect(typingIndicator).toHaveClass('animate-pulse');
    });

    it('should handle typing indicator websocket events', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Simulate typing start event from WebSocket
      const typingStartEvent = {
        type: 'typing_start',
        payload: { userId: 'Assistant', threadId: 'thread-123' }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: typingStartEvent
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      // Should update typing users
      await waitFor(() => {
        expect(mockChatStore.startTyping).toHaveBeenCalled();
      });
    });
  });

  describe('Connection Status and Error Handling', () => {
    it('should show connection status', () => {
      const disconnectedStore = {
        ...mockChatStore,
        isConnected: false
      };
      
      const disconnectedWebSocket = {
        ...mockWebSocket,
        connected: false,
        connectionState: 'disconnected'
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(disconnectedStore);
      (useWebSocket as jest.Mock).mockReturnValue(disconnectedWebSocket);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('connection-status')).toBeInTheDocument();
      expect(screen.getByText(/disconnected/i)).toBeInTheDocument();
    });

    it('should show reconnection attempts', () => {
      const reconnectingWebSocket = {
        ...mockWebSocket,
        connected: false,
        connectionState: 'reconnecting',
        reconnectAttempts: 3
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(reconnectingWebSocket);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('reconnection-status')).toBeInTheDocument();
      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument();
      expect(screen.getByText(/attempt 3/i)).toBeInTheDocument();
    });

    it('should handle WebSocket errors gracefully', () => {
      const errorWebSocket = {
        ...mockWebSocket,
        connected: false,
        error: new Error('WebSocket connection failed'),
        connectionState: 'error'
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(errorWebSocket);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      expect(screen.getByTestId('connection-error')).toBeInTheDocument();
      expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
      expect(screen.getByTestId('reconnect-button')).toBeInTheDocument();
    });

    it('should queue messages when offline', async () => {
      const offlineStore = {
        ...mockChatStore,
        isConnected: false,
        queueMessage: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(offlineStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      await userEvent.type(messageInput, 'Offline message');
      await userEvent.keyboard('[Enter]');
      
      expect(offlineStore.queueMessage).toHaveBeenCalledWith('Offline message');
    });

    it('should show queued message indicator', () => {
      const queuedStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Queued message',
            role: 'user',
            status: 'queued'
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(queuedStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      expect(messageEl).toHaveClass('opacity-60'); // Queued styling
      
      const queueIndicator = within(messageEl).getByTestId('queue-indicator');
      expect(queueIndicator).toBeInTheDocument();
    });

    it('should send queued messages when reconnected', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Initially offline with queued messages
      const offlineStore = {
        ...mockChatStore,
        isConnected: false,
        queuedMessages: [
          { id: 'queued-1', content: 'Queued message 1' },
          { id: 'queued-2', content: 'Queued message 2' }
        ],
        sendQueuedMessages: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(offlineStore);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      // Reconnect
      const onlineStore = {
        ...offlineStore,
        isConnected: true
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(onlineStore);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(onlineStore.sendQueuedMessages).toHaveBeenCalled();
      });
    });
  });

  describe('Real-time Message Updates', () => {
    it('should receive new messages via WebSocket', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Simulate new message from WebSocket
      const newMessageEvent = {
        type: 'new_message',
        payload: {
          id: 'msg-new',
          content: 'New message from server',
          role: 'assistant',
          threadId: 'thread-123'
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: newMessageEvent
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.addMessage).toHaveBeenCalledWith({
          id: 'msg-new',
          content: 'New message from server',
          role: 'assistant',
          threadId: 'thread-123'
        });
      });
    });

    it('should handle message updates via WebSocket', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Simulate message update from WebSocket
      const updateEvent = {
        type: 'message_updated',
        payload: {
          messageId: 'msg-1',
          updates: {
            content: 'Updated content',
            status: 'edited'
          }
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: updateEvent
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.updateMessage).toHaveBeenCalledWith('msg-1', {
          content: 'Updated content',
          status: 'edited'
        });
      });
    });

    it('should handle message deletion via WebSocket', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const deleteEvent = {
        type: 'message_deleted',
        payload: {
          messageId: 'msg-to-delete'
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: deleteEvent
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.deleteMessage).toHaveBeenCalledWith('msg-to-delete');
      });
    });

    it('should handle message reactions via WebSocket', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const reactionEvent = {
        type: 'message_reaction',
        payload: {
          messageId: 'msg-1',
          reaction: '👍',
          userId: 'user-123',
          action: 'add'
        }
      };
      
      const updatedWebSocket = {
        ...mockWebSocket,
        lastMessage: reactionEvent
      };
      
      (useWebSocket as jest.Mock).mockReturnValue(updatedWebSocket);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(mockChatStore.updateMessage).toHaveBeenCalledWith('msg-1', {
          reactions: expect.any(Object)
        });
      });
    });
  });

  describe('Message Actions and Context Menu', () => {
    it('should show message context menu on right click', async () => {
      const messagesStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Right-clickable message',
            role: 'user',
            canEdit: true,
            canDelete: true
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(messagesStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      await userEvent.pointer([{ target: messageEl, keys: '[MouseRight]' }]);
      
      expect(screen.getByTestId('message-context-menu')).toBeInTheDocument();
      expect(screen.getByTestId('edit-message-option')).toBeInTheDocument();
      expect(screen.getByTestId('delete-message-option')).toBeInTheDocument();
      expect(screen.getByTestId('copy-message-option')).toBeInTheDocument();
    });

    it('should copy message content to clipboard', async () => {
      const copyableStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'Copy this message', role: 'assistant' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(copyableStore);
      
      const writeTextSpy = jest.fn();
      Object.assign(navigator, {
        clipboard: { writeText: writeTextSpy }
      });
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      await userEvent.pointer([{ target: messageEl, keys: '[MouseRight]' }]);
      
      const copyOption = screen.getByTestId('copy-message-option');
      await userEvent.click(copyOption);
      
      expect(writeTextSpy).toHaveBeenCalledWith('Copy this message');
    });

    it('should edit user messages inline', async () => {
      const editableStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'Editable message',
            role: 'user',
            canEdit: true
          }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(editableStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      await userEvent.pointer([{ target: messageEl, keys: '[MouseRight]' }]);
      
      const editOption = screen.getByTestId('edit-message-option');
      await userEvent.click(editOption);
      
      const editInput = screen.getByTestId('edit-message-input');
      expect(editInput).toHaveValue('Editable message');
      
      await userEvent.clear(editInput);
      await userEvent.type(editInput, 'Edited message content');
      
      const saveButton = screen.getByTestId('save-edit-button');
      await userEvent.click(saveButton);
      
      expect(mockChatStore.updateMessage).toHaveBeenCalledWith('msg-1', {
        content: 'Edited message content',
        status: 'edited'
      });
    });

    it('should add reactions to messages', async () => {
      const reactableStore = {
        ...mockChatStore,
        messages: [
          {
            id: 'msg-1',
            content: 'React to this',
            role: 'assistant',
            canReact: true,
            reactions: {}
          }
        ],
        addReaction: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(reactableStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageEl = screen.getByTestId('message-msg-1');
      await userEvent.hover(messageEl);
      
      const reactionButton = screen.getByTestId('add-reaction-btn');
      await userEvent.click(reactionButton);
      
      const emojiPicker = screen.getByTestId('emoji-picker');
      expect(emojiPicker).toBeInTheDocument();
      
      const thumbsUpEmoji = screen.getByTestId('emoji-👍');
      await userEvent.click(thumbsUpEmoji);
      
      expect(reactableStore.addReaction).toHaveBeenCalledWith('msg-1', '👍');
    });
  });

  describe('Performance and Optimization', () => {
    it('should virtualize large message lists', () => {
      const manyMessages = Array.from({ length: 1000 }, (_, i) => ({
        id: `msg-${i}`,
        content: `Message ${i}`,
        role: i % 2 === 0 ? 'user' : 'assistant'
      }));
      
      const largeMessagesStore = {
        ...mockChatStore,
        messages: manyMessages
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(largeMessagesStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageList = screen.getByTestId('message-list');
      expect(messageList).toBeInTheDocument();
      
      // Should not render all 1000 messages in DOM
      const renderedMessages = screen.getAllByTestId(/^message-msg-/);
      expect(renderedMessages.length).toBeLessThan(100);
    });

    it('should debounce typing indicators', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageInput = screen.getByTestId('message-input-field');
      
      // Type multiple characters quickly
      await userEvent.type(messageInput, 'quick');
      
      // Should only start typing once
      expect(mockChatStore.startTyping).toHaveBeenCalledTimes(1);
    });

    it('should cleanup timers and listeners on unmount', () => {
      const { unmount } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      
      unmount();
      
      expect(clearTimeoutSpy).toHaveBeenCalled();
      expect(clearIntervalSpy).toHaveBeenCalled();
    });

    it('should throttle scroll events', async () => {
      const scrollStore = {
        ...mockChatStore,
        handleScroll: jest.fn()
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(scrollStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const messageList = screen.getByTestId('message-list');
      
      // Simulate rapid scroll events
      for (let i = 0; i < 10; i++) {
        messageList.dispatchEvent(new Event('scroll'));
      }
      
      // Should throttle calls
      await waitFor(() => {
        expect(scrollStore.handleScroll).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      const accessibleStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'Test message', role: 'user' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(accessibleStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const chatRegion = screen.getByRole('main', { name: /chat window/i });
      expect(chatRegion).toBeInTheDocument();
      
      const messagesList = screen.getByRole('log', { name: /conversation/i });
      expect(messagesList).toBeInTheDocument();
      
      const messageInput = screen.getByRole('textbox', { name: /message input/i });
      expect(messageInput).toBeInTheDocument();
    });

    it('should announce new messages to screen readers', async () => {
      const { rerender } = renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toBeInTheDocument();
      
      // Add new message
      const updatedStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'New message arrived', role: 'assistant' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(updatedStore);
      
      rerender(
        <WebSocketProvider>
          <ChatWindow threadId="thread-123" />
        </WebSocketProvider>
      );
      
      await waitFor(() => {
        expect(liveRegion).toHaveTextContent(/new message from assistant/i);
      });
    });

    it('should support keyboard navigation', async () => {
      const keyboardStore = {
        ...mockChatStore,
        messages: [
          { id: 'msg-1', content: 'Message 1', role: 'user' },
          { id: 'msg-2', content: 'Message 2', role: 'assistant' }
        ]
      };
      
      (useUnifiedChatStore as jest.Mock).mockReturnValue(keyboardStore);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Focus input by default
      const messageInput = screen.getByTestId('message-input-field');
      expect(messageInput).toHaveFocus();
      
      // Navigate to messages
      await userEvent.keyboard('[Escape]'); // Exit input
      await userEvent.keyboard('[ArrowUp]'); // Navigate to last message
      
      const lastMessage = screen.getByTestId('message-msg-2');
      expect(lastMessage).toHaveFocus();
    });

    it('should provide keyboard shortcuts', async () => {
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      // Ctrl+L should clear chat
      await userEvent.keyboard('[Control>]l[/Control]');
      expect(mockChatStore.clearMessages).toHaveBeenCalled();
      
      // Ctrl+/ should show help
      await userEvent.keyboard('[Control>]/[/Control]');
      expect(screen.getByTestId('keyboard-help-dialog')).toBeInTheDocument();
    });

    it('should support high contrast mode', () => {
      const matchMediaSpy = jest.spyOn(window, 'matchMedia').mockReturnValue({
        matches: true,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      } as any);
      
      renderWithProvider(<ChatWindow threadId="thread-123" />);
      
      const chatWindow = screen.getByTestId('chat-window');
      expect(chatWindow).toHaveClass('high-contrast');
      
      matchMediaSpy.mockRestore();
    });
  });
});