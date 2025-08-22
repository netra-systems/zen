/**
 * First-time user onboarding welcome screen tests
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock hooks and stores
const mockUseUnifiedChatStore = jest.fn();
const mockUseWebSocket = jest.fn();
const mockUseLoadingState = jest.fn();
const mockUseEventProcessor = jest.fn();
const mockUseThreadNavigation = jest.fn();

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

// Mock child components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => React.createElement('div', { 'data-testid': 'chat-header' }, 'Chat Header')
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => React.createElement('div', { 'data-testid': 'message-list' }, 'Message List')
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => React.createElement('div', { 'data-testid': 'message-input' }, 'Message Input')
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

jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn()
  }
}));

// Import component after mocks
import MainChat from '@/components/chat/MainChat';

describe('First-Time User Onboarding Welcome', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock implementations for first-time user state
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [], // No messages for first-time user
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
      shouldShowEmptyState: true, // Show welcome for first-time user
      shouldShowExamplePrompts: true,
      loadingMessage: ''
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null, // No thread selected for first-time user
      isNavigating: false
    });
  });

  it('shows welcome header for first-time users', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Your AI-powered optimization platform for reducing costs and improving performance')).toBeInTheDocument();
  });

  it('displays onboarding steps guide', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Get Started in 3 Easy Steps:')).toBeInTheDocument();
    });
    
    // Check for all 3 steps
    expect(screen.getByText(/Choose an example prompt below/)).toBeInTheDocument();
    expect(screen.getByText(/Describe your current setup/)).toBeInTheDocument();
    expect(screen.getByText(/Get AI-powered recommendations/)).toBeInTheDocument();
  });

  it('shows example prompts section for new users', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });
  });

  it('shows helpful tip for first-time users', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText(/Try typing something like:/)).toBeInTheDocument();
      expect(screen.getByText(/I need to reduce my AI costs by 30% while maintaining quality/)).toBeInTheDocument();
    });
  });

  it('hides welcome content when user has messages', async () => {
    // Simulate user with existing messages
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [{ id: '1', content: 'Test message', role: 'user' }],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread-1',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false, // No welcome for existing users
      shouldShowExamplePrompts: false,
      loadingMessage: ''
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
    });
  });

  it('shows message input for interaction', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
    });
  });
});
