/**
 * E2E Chat Interaction Tests - Core Module
 * 
 * Business Value: Core chat revenue protection
 * Priority: P0 - Critical path testing
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';
import { MessageInput } from '@/components/chat/MessageInput';
import { MessageItem } from '@/components/chat/MessageItem';
import MainChat from '@/components/chat/MainChat'; // Default import
import type { Message } from '@/types/registry';
import { TestProviders } from '../setup/test-providers';

// Test message factories (8 lines max each)
const createTestMessage = (overrides = {}): Message => ({
  id: 'test-msg-123',
  content: 'Test message content',
  type: 'user',
  role: 'user',
  timestamp: Date.now(),
  ...overrides
});

const createAIMessage = (overrides = {}): Message => ({
  id: 'ai-msg-456',
  content: 'AI response content',
  type: 'assistant',
  role: 'assistant',
  timestamp: Date.now(),
  ...overrides
});

// Test utilities (8 lines max each)
const renderWithWebSocket = (component: React.ReactElement) => {
  const wsManager = new WebSocketTestManager();
  wsManager.setup();
  const result = render(
    <TestProviders>
      {component}
    </TestProviders>
  );
  return { ...result, wsManager };
};

const expectSendButtonEnabled = (enabled: boolean) => {
  const sendButton = screen.getByRole('button', { name: /send/i });
  if (enabled) {
    expect(sendButton).toBeEnabled();
  } else {
    expect(sendButton).toBeDisabled();
  }
};

// Mock stores for testing
const mockAuthStore = {
  isAuthenticated: true,
  user: { id: 'user-123' },
  token: 'test-token'
};

// Mock required hooks
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: true, // Show loading by default
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Loading chat...'
  })
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: () => ({})
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: () => ({
    currentThreadId: null,
    isNavigating: false
  })
}));

const mockChatStore = {
  threads: [],
  activeThreadId: 'thread-123',
  messages: [],
  isProcessing: false,
  sendMessage: jest.fn(),
  addOptimisticMessage: jest.fn(),
  handleWebSocketEvent: jest.fn(),
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  isThreadLoading: false
};

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => mockAuthStore
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => mockChatStore
}));

describe('Chat Input Basic Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
    jest.clearAllMocks();
  });

  it('handles text input correctly', async () => {
    const { wsManager } = renderWithWebSocket(<MessageInput />);
    
    const input = screen.getByRole('textbox', { name: /message input/i });
    await user.type(input, 'Hello world');
    
    expect(input).toHaveValue('Hello world');
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('handles emoji input correctly', async () => {
    const { wsManager } = renderWithWebSocket(<MessageInput />);
    
    const input = screen.getByRole('textbox', { name: /message input/i });
    await user.type(input, '👋 Hello! 🎉');
    
    expect(input).toHaveValue('👋 Hello! 🎉');
    expectSendButtonEnabled(true);
    wsManager.cleanup();
  });

  it('disables send button when empty', async () => {
    const { wsManager } = renderWithWebSocket(<MessageInput />);
    
    expectSendButtonEnabled(false);
    wsManager.cleanup();
  });

  it('sends message on Enter key', async () => {
    const { wsManager } = renderWithWebSocket(<MessageInput />);
    
    const input = screen.getByRole('textbox', { name: /message input/i });
    await user.type(input, 'Test message{enter}');
    
    expect(input).toHaveValue('');
    wsManager.cleanup();
  });
});

describe('Message Display Tests', () => {
  it('renders user message correctly', async () => {
    const testMessage = createTestMessage({ content: 'Hello world' });
    const { wsManager } = renderWithWebSocket(
      <MessageItem message={testMessage} />
    );
    
    expect(screen.getByText('Hello world')).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('renders AI message correctly', async () => {
    const aiMessage = createAIMessage({ content: 'AI response' });
    const { wsManager } = renderWithWebSocket(
      <MessageItem message={aiMessage} />
    );
    
    expect(screen.getByText('AI response')).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('handles special characters correctly', async () => {
    const specialMessage = createTestMessage({ 
      content: 'Special ~!@#$%^&*() characters' 
    });
    const { wsManager } = renderWithWebSocket(
      <MessageItem message={specialMessage} />
    );
    
    expect(screen.getByText('Special ~!@#$%^&*() characters')).toBeInTheDocument();
    wsManager.cleanup();
  });
});

describe('MainChat Integration Tests', () => {
  let user: ReturnType<typeof userEvent.setup>;
  
  beforeEach(() => {
    user = userEvent.setup();
  });

  it('renders chat interface correctly', async () => {
    const { wsManager } = renderWithWebSocket(<MainChat />);
    
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: /message input/i })).toBeInTheDocument();
    wsManager.cleanup();
  });

  it('handles message input and sending', async () => {
    const { wsManager } = renderWithWebSocket(<MainChat />);
    
    const input = screen.getByRole('textbox', { name: /message input/i });
    await user.type(input, 'Test message');
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);
    
    expect(mockChatStore.sendMessage).toHaveBeenCalled();
    wsManager.cleanup();
  });

  it('shows loading state initially', async () => {
    const { wsManager } = renderWithWebSocket(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Loading chat...')).toBeInTheDocument();
    });
    wsManager.cleanup();
  });
});



