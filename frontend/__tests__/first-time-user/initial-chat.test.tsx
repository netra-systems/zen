/**
 * First-time user initial chat interaction tests
 */

// CRITICAL: Mock lucide-react FIRST before any other imports
jest.mock('lucide-react', () => {
  const React = require('react');
  return {
    // Existing icons
    Command: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Command', ...props }),
    ArrowUp: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'ArrowUp', ...props }),
    ArrowDown: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'ArrowDown', ...props }),
    Loader2: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Loader2', 'data-testid': 'loader2-icon', ...props }),
    
    // ChatHeader and component icons
    Bot: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Bot', ...props }),
    Zap: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Zap', ...props }),
    Activity: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Activity', ...props }),
    Shield: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Shield', ...props }),
    Database: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Database', ...props }),
    Cpu: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Cpu', ...props }),
    Brain: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Brain', ...props }),
    
    // MCPServerStatus icons
    Server: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Server', ...props }),
    Wifi: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Wifi', ...props }),
    WifiOff: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'WifiOff', ...props }),
    AlertTriangle: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'AlertTriangle', ...props }),
    CheckCircle2: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'CheckCircle2', ...props }),
    Clock: ({ className = '', ...props }) => React.createElement('div', { className, 'data-icon': 'Clock', ...props })
  };
});

// Mock framer-motion SECOND
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => React.createElement('div', props, children)
  },
  AnimatePresence: ({ children }) => React.createElement(React.Fragment, {}, children)
}));

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock all required modules
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseEventProcessor = jest.fn();
const mockUseThreadNavigation = jest.fn();
const mockUseAuthStore = jest.fn();
const mockUseMessageSending = jest.fn();
const mockUseThreadStore = jest.fn();
const mockUseMessageHistory = jest.fn();
const mockUseTextareaResize = jest.fn();

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

// Mock the WebSocket provider completely
jest.mock('@/providers/WebSocketProvider', () => require('@/__mocks__/providers/WebSocketProvider'));

// Mock WebSocket provider context
jest.mock('@/providers/WebSocketProvider', () => ({
  useWebSocketContext: jest.fn().mockReturnValue({
    status: 'OPEN',
    isConnected: true,
    send: jest.fn(),
    disconnect: jest.fn()
  }),
  WebSocketProvider: ({ children }) => React.createElement('div', {}, children)
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => {
    const mockInstance = mockUseLoadingState();
    // Ensure we always return a proper mock with consistent values
    return {
      loadingState: mockInstance.loadingState || 'READY',
      shouldShowLoading: mockInstance.shouldShowLoading || false,
      shouldShowEmptyState: mockInstance.shouldShowEmptyState !== undefined ? mockInstance.shouldShowEmptyState : true,
      shouldShowExamplePrompts: mockInstance.shouldShowExamplePrompts !== undefined ? mockInstance.shouldShowExamplePrompts : true,
      loadingMessage: mockInstance.loadingMessage || '',
      isInitialized: mockInstance.isInitialized !== undefined ? mockInstance.isInitialized : true
    };
  }
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: mockUseEventProcessor
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: mockUseThreadStore
}));

jest.mock('@/components/chat/hooks/useMessageSending', () => ({
  useMessageSending: mockUseMessageSending
}));

jest.mock('@/components/chat/hooks/useMessageHistory', () => ({
  useMessageHistory: mockUseMessageHistory
}));

jest.mock('@/components/chat/hooks/useTextareaResize', () => ({
  useTextareaResize: mockUseTextareaResize
}));

// Mock additional services needed by useMessageSending
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    createThread: jest.fn().mockResolvedValue({ id: 'test-thread-id', title: 'Test Thread' }),
    getThread: jest.fn().mockResolvedValue({ id: 'test-thread-id', metadata: {} })
  }
}));

jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn()
  }
}));

jest.mock('@/services/optimistic-updates', () => ({
  optimisticMessageManager: {
    addOptimisticUserMessage: jest.fn().mockReturnValue({ id: 'opt-user', localId: 'opt-user-local' }),
    addOptimisticAiMessage: jest.fn().mockReturnValue({ id: 'opt-ai', localId: 'opt-ai-local' }),
    getFailedMessages: jest.fn().mockReturnValue([]),
    retryMessage: jest.fn().mockResolvedValue(undefined)
  }
}));

jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: jest.fn().mockReturnValue({
    trackChatStarted: jest.fn(),
    trackMessageSent: jest.fn(),
    trackThreadCreated: jest.fn(),
    trackError: jest.fn(),
    trackAgentActivated: jest.fn()
  })
}));

// Mock child components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => React.createElement('div', { 'data-testid': 'chat-header' }, 'Chat Header')
}));

// Mock ChatHeader dependencies  
jest.mock('@/components/chat/ConnectionStatusIndicator', () => ({
  __esModule: true,
  default: () => React.createElement('div', { 'data-testid': 'connection-status' }, 'Connected')
}));

jest.mock('@/components/chat/MCPServerStatus', () => ({
  MCPServerStatus: () => React.createElement('div', { 'data-testid': 'mcp-status' }, 'MCP Status')
}));

jest.mock('@/hooks/useMCPTools', () => ({
  useMCPTools: jest.fn().mockReturnValue({
    servers: [],
    executions: []
  })
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => React.createElement('div', { 'data-testid': 'message-list' }, 'Message List')
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => React.createElement('div', { 'data-testid': 'example-prompts' }, 'Example Prompts')
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: () => React.createElement('div', { 'data-testid': 'response-card' }, 'Response Card')
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => React.createElement('div', { 'data-testid': 'overflow-panel' }, 'Overflow Panel')
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => React.createElement('div', { 'data-testid': 'diagnostics-panel' }, 'Diagnostics Panel')
}));

jest.mock('@/components/chat/components/MessageActionButtons', () => ({
  MessageActionButtons: () => React.createElement('div', { 'data-testid': 'action-buttons' }, 'Actions')
}));

// No mock needed for KeyboardShortcutsHint - using simple icon replacement


jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn()
  }
}));

// Remove the mock for messageInputUtils to use the real implementation

jest.mock('@/components/chat/types', () => ({
  MESSAGE_INPUT_CONSTANTS: {
    MAX_ROWS: 5,
    CHAR_LIMIT: 10000,
    LINE_HEIGHT: 24
  }
}));

// Don't mock MessageInput - use the real component

// Import components after mocks
import MainChat from '@/components/chat/MainChat';
import { MessageInput } from '@/components/chat/MessageInput';

describe('First-Time User Initial Chat', () => {
  const mockHandleSend = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default auth state - authenticated user
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });
    
    // Default chat store state for new user
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseWebSocket.mockReturnValue({
      messages: [],
      status: 'OPEN',
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      isConnected: true
    });
    
    // FIXED: Set loading state properly to show content instead of loading spinner
    mockUseLoadingState.mockReturnValue({
      loadingState: 'READY',
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: '',
      isInitialized: true
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    });
    
    mockUseThreadStore.mockReturnValue({
      currentThreadId: null
    });
    
    mockUseMessageHistory.mockReturnValue({
      messageHistory: [],
      addToHistory: jest.fn(),
      navigateHistory: jest.fn(() => '')
    });
    
    mockUseTextareaResize.mockReturnValue({
      rows: 1
    });
    
    mockUseMessageSending.mockReturnValue({
      isSending: false,
      handleSend: mockHandleSend
    });
  });

  it('allows first-time user to type in message input', () => {
    // Override the beforeEach mock to ensure fresh setup
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });
    
    render(<MessageInput />);
    
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeInTheDocument();
    
    // Debug: check what the placeholder says
    console.log('Placeholder text:', textarea.getAttribute('placeholder'));
    
    expect(textarea).not.toBeDisabled();
    
    fireEvent.change(textarea, { target: { value: 'Hello Netra!' } });
    expect(textarea).toHaveValue('Hello Netra!');
  });

  it('shows example prompts for first-time users', async () => {
    // Force the loading state to immediately show example prompts
    mockUseLoadingState.mockReturnValue({
      loadingState: 'READY',
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: '',
      isInitialized: true
    });
    
    // Ensure WebSocket is properly mocked as connected
    mockUseWebSocket.mockReturnValue({
      messages: [],
      status: 'OPEN',
      connect: jest.fn(),
      disconnect: jest.fn(),
      send: jest.fn(),
      isConnected: true
    });
    
    // Ensure no thread is active to show empty state
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('handles message sending for first-time user', async () => {
    // Set up proper authentication state
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    });
    
    render(<MessageInput />);
    
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'My first optimization request' } });
    
    console.log('Message sending test - Value after change:', textarea.value);
    
    // Simulate Enter key press to send message
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    
    // Wait for async operations to complete
    await waitFor(() => {
      expect(mockHandleSend).toHaveBeenCalled();
    }, { timeout: 1000 });
    
    console.log('Message sending test - handleSend calls:', mockHandleSend.mock.calls.length);
    console.log('Message sending test - handleSend call args:', mockHandleSend.mock.calls);
  });

  it('shows processing state when user sends first message', async () => {
    // Simulate processing state after sending first message
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: true,
      messages: [],
      fastLayerData: { status: 'Processing your request...' },
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: 'run-123',
      activeThreadId: 'thread-1',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseLoadingState.mockReturnValue({
      loadingState: 'PROCESSING',
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Processing...',
      isInitialized: true
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: 'thread-1',
      isNavigating: false
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });
  });

  it('transitions from empty state to chat after first message', async () => {
    // Start with empty state
    mockUseLoadingState.mockReturnValue({
      loadingState: 'READY',
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: '',
      isInitialized: true
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
    
    // Simulate after sending first message - should hide welcome
    mockUseLoadingState.mockReturnValue({
      loadingState: 'THREAD_READY',
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: '',
      isInitialized: true
    });
    
    // Re-render with updated state
    render(<MainChat />);
    
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
  });

  it('shows message input is always available for interaction', async () => {
    // Set up proper state to render content
    mockUseLoadingState.mockReturnValue({
      loadingState: 'READY',
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: '',
      isInitialized: true
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });
  });

  it('disables input when user is not authenticated', () => {
    // Set up non-authenticated state  
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });
    
    // Reset other mocks to ensure fresh state
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseThreadStore.mockReturnValue({
      currentThreadId: null
    });
    
    mockUseMessageHistory.mockReturnValue({
      messageHistory: [],
      addToHistory: jest.fn(),
      navigateHistory: jest.fn(() => '')
    });
    
    mockUseTextareaResize.mockReturnValue({
      rows: 1
    });
    
    mockUseMessageSending.mockReturnValue({
      isSending: false,
      handleSend: mockHandleSend
    });
    
    render(<MessageInput />);
    
    const textarea = screen.getByRole('textbox');
    console.log('Disabled test - Placeholder text:', textarea.getAttribute('placeholder'));
    console.log('Disabled test - isDisabled:', textarea.hasAttribute('disabled'));
    expect(textarea).toBeDisabled();
  });
});
