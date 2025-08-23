/**
 * First-time user initial chat interaction tests
 */

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

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
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

// Mock child components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => React.createElement('div', { 'data-testid': 'chat-header' }, 'Chat Header')
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

jest.mock('@/components/chat/components/KeyboardShortcutsHint', () => ({
  KeyboardShortcutsHint: () => React.createElement('div', { 'data-testid': 'keyboard-hint' }, 'Hint')
}));

jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn()
  }
}));

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
      messages: []
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: ''
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
    
    // Setup remaining hooks that the working test has
    mockUseWebSocket.mockReturnValue({
      messages: []
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    });
    
    // Default loading state for first-time user
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: ''
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
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });
  });

  it('handles message sending for first-time user', () => {
    render(<MessageInput />);
    
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'My first optimization request' } });
    
    // Simulate Enter key press to send message
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    
    expect(mockHandleSend).toHaveBeenCalled();
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
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: ''
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
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
    
    // Simulate after sending first message - should hide welcome
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: ''
    });
    
    // Re-render with updated state
    render(<MainChat />);
    
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
  });

  it('shows message input is always available for interaction', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });
  });

  it('disables input when user is not authenticated', () => {
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false
    });
    
    render(<MessageInput />);
    
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });
});
