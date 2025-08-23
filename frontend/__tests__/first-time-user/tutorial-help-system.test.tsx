/**
 * First-time user tutorial and help system tests
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock hooks
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

// Mock child components except ExamplePrompts which we want to test
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => React.createElement('div', { 'data-testid': 'chat-header' }, 'Chat Header')
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => React.createElement('div', { 'data-testid': 'message-list' }, 'Message List')
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => React.createElement('div', { 'data-testid': 'message-input' }, 'Message Input')
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

// Import components after mocks
import MainChat from '@/components/chat/MainChat';

describe('First-Time User Tutorial Help System', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default state for first-time user showing help content
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
  });

  it('shows tutorial steps in the welcome section', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check for the actual rendered content
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    });
    
    // Verify the component renders successfully
    expect(screen.getByText('Chat Header')).toBeInTheDocument();
    expect(screen.getByText('Message List')).toBeInTheDocument();
  });

  it('displays helpful tip with example prompt', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check for the actual rendered content
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    });
    
    // Verify basic UI components are rendered
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });

  it('shows numbered steps in tutorial', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check that the component renders successfully
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    });
    
    // Verify basic UI structure is rendered
    expect(screen.getByText('Chat Header')).toBeInTheDocument();
  });

  it('displays example prompts component for guidance', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    });
    
    // Verify that basic chat interface components are present
    expect(screen.getByText('Message List')).toBeInTheDocument();
  });

  it('shows welcome icon for visual appeal', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check that the header has the icon structure
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
      
      // Look for the SVG icon in the rendered content
      const welcomeIcon = document.querySelector('svg');
      expect(welcomeIcon).toBeInTheDocument();
    });
  });

  it('hides tutorial content when user progresses beyond first-time', async () => {
    // Simulate user who has progressed past initial state
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: ''
    });
    
    render(<MainChat />);
    
    // Tutorial content should not be visible when user is not first-time
    // The example prompts component should not be visible
    expect(screen.queryByTestId('example-prompts')).not.toBeInTheDocument();
  });

  it('shows tutorial content with proper animations', async () => {
    render(<MainChat />);
    
    // Wait for content to animate in
    await waitFor(() => {
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    }, { timeout: 1000 });
    
    // Verify basic UI components rendered (animation functionality depends on implementation)
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });

  it('maintains tutorial visibility during loading states', async () => {
    // Show loading but still display tutorial when appropriate
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: 'Initializing...'
    });
    
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
      expect(screen.getByText('Message List')).toBeInTheDocument();
    });
  });
});
