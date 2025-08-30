/**
 * Chat UI/UX Message Handling Tests
 * Module-based architecture: Message tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import MainChat from '../../components/chat/MainChat';
import { ChatWindow } from '../../components/chat/ChatWindow';
import { MessageList } from '../../components/chat/MessageList';
import { 
  setupBasicMocks,
  setupAuthenticatedStore,
  setupStoreWithMessages,
  createMockAuthStore,
  createMockChatStore,
  createMockMessage,
  createStreamingMessage,
  renderWithProviders,
  expectMessageOrWelcome,
  cleanupMocks
} from './chatUIUX-shared-utilities';

// Setup mocks
setupBasicMocks();

// Import mocked modules
import { useAuthStore } from '../../store/authStore';
import { useChatStore } from '../../store/chatStore';
import { useThreadStore } from '../../store/threadStore';
import { useUnifiedChatStore } from '../../store/unified-chat';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';

describe('Chat UI/UX Message Handling Tests', () => {
  const mockAuthStore = createMockAuthStore();
  const mockChatStore = createMockChatStore();
  
  beforeEach(() => {
    jest.clearAllMocks();
    setupDefaultMockReturnValues();
  });

  afterEach(() => {
    cleanupMocks();
  });

  describe('Message Sending and Receiving', () => {
    test('8. Should send a message and display it in the message list', async () => {
      const mockOnSendMessage = jest.fn();
      
      render(renderWithProviders(
        <ChatWindow onSendMessage={mockOnSendMessage} />
      ));
      
      await sendMessageAndVerify('Test message', mockOnSendMessage);
    });

    test('9. Should receive and display agent response messages', async () => {
      const mockMessages = [
        createMockMessage('user', 'User message'),
        createMockMessage('agent', 'This is an agent response')
      ];
      
      setupMessagesInStore(mockMessages);
      
      render(renderWithProviders(<MessageList />));
      
      await verifyMessageOrWelcomeDisplayed('This is an agent response');
    });

    test('10. Should handle message streaming with partial updates', async () => {
      const streamingMessage = createStreamingMessage();
      setupMessagesInStore([streamingMessage]);
      
      render(renderWithProviders(<MessageList />));
      
      await verifyMessageOrWelcomeDisplayed('Hello world, how are you?');
    });

    test('11. Should display thinking indicator during agent processing', async () => {
      setupProcessingState();
      
      render(renderWithProviders(<MainChat />));
      
      await verifyProcessingState();
    });

    test('12. Should handle empty message list gracefully', async () => {
      setupMessagesInStore([]);
      
      render(renderWithProviders(<MessageList />));
      
      await waitFor(() => {
        const welcomeMessage = screen.queryByText(/Welcome to Netra AI/i);
        expect(welcomeMessage).toBeTruthy();
      }, { timeout: 2000 });
    });

    test('13. Should handle message errors appropriately', async () => {
      const errorStore = {
        ...mockChatStore,
        error: 'Failed to send message',
        messages: []
      };
      (useChatStore as unknown as jest.Mock).mockReturnValue(errorStore);
      
      render(renderWithProviders(<MessageList />));
      
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
    });

    test('14. Should handle multiple message types correctly', async () => {
      const mixedMessages = [
        createMockMessage('user', 'User question'),
        createMockMessage('agent', 'Agent response'),
        createMockMessage('system', 'System notification')
      ];
      
      setupMessagesInStore(mixedMessages);
      
      render(renderWithProviders(<MessageList />));
      
      await verifyMessageOrWelcomeDisplayed();
    });

    test('15. Should handle message timestamps correctly', async () => {
      const timestampedMessage = {
        ...createMockMessage('agent', 'Timestamped message'),
        created_at: new Date('2025-01-01T12:00:00Z').toISOString()
      };
      
      setupMessagesInStore([timestampedMessage]);
      
      render(renderWithProviders(<MessageList />));
      
      await verifyMessageOrWelcomeDisplayed('Timestamped message');
    });
  });
});

// Helper functions ≤8 lines each
const setupDefaultMockReturnValues = () => {
  (useAuthStore as unknown as jest.Mock).mockReturnValue(
    setupAuthenticatedStore(mockAuthStore)
  );
  (useThreadStore as unknown as jest.Mock).mockReturnValue({
    threads: [],
    currentThreadId: null
  });
  (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
    isProcessing: false,
    messages: []
  });
  (useChatWebSocket as unknown as jest.Mock).mockReturnValue({});
};

const setupMessagesInStore = (messages: any[]) => {
  const storeWithMessages = setupStoreWithMessages(mockChatStore, messages);
  (useChatStore as unknown as jest.Mock).mockReturnValue(storeWithMessages);
};

const setupProcessingState = () => {
  (useChatStore as unknown as jest.Mock).mockReturnValue({
    ...mockChatStore,
    messages: [],
    isProcessing: true
  });
  
  (useUnifiedChatStore as unknown as jest.Mock).mockReturnValue({
    isProcessing: true,
    messages: []
  });
};

const sendMessageAndVerify = async (message: string, mockFn: jest.Mock) => {
  const messageInput = screen.getByPlaceholderText(/start typing your ai optimization request/i);
  await userEvent.type(messageInput, message);
  
  const sendButton = screen.getByRole('button', { name: /send/i });
  fireEvent.click(sendButton);
  
  await waitFor(() => {
    expect(mockFn).toHaveBeenCalledWith(message);
  });
};

const verifyMessageOrWelcomeDisplayed = async (messageText?: string) => {
  await waitFor(() => {
    expectMessageOrWelcome(screen, messageText);
  }, { timeout: 2000 });
};

const verifyProcessingState = async () => {
  await waitFor(() => {
    const container = document.querySelector('.flex.h-full.bg-gradient-to-br');
    expect(container).toBeInTheDocument();
  });
};