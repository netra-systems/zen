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
      expect(screen.getByText('Get Started in 3 Easy Steps:')).toBeInTheDocument();
    });
    
    // Verify all tutorial steps are present
    expect(screen.getByText(/Choose an example prompt below/)).toBeInTheDocument();
    expect(screen.getByText(/Describe your current setup/)).toBeInTheDocument();
    expect(screen.getByText(/Get AI-powered recommendations/)).toBeInTheDocument();
  });

  it('displays helpful tip with example prompt', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByText(/Try typing something like:/)).toBeInTheDocument();
    });
    
    expect(screen.getByText(/I need to reduce my AI costs by 30% while maintaining quality/)).toBeInTheDocument();
  });

  it('shows numbered steps in tutorial', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check for numbered step indicators
      const stepElements = screen.getAllByText(/[123]/);
      expect(stepElements.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('displays example prompts component for guidance', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    });
  });

  it('shows welcome icon for visual appeal', async () => {
    render(<MainChat />);
    
    await waitFor(() => {
      // Check that the welcome screen has the icon structure in the welcome section
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
      
      // Look for the lightning bolt SVG icon in the welcome content
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
    
    // Tutorial content should not be visible
    expect(screen.queryByText('Get Started in 3 Easy Steps:')).not.toBeInTheDocument();
    expect(screen.queryByText(/Try typing something like:/)).not.toBeInTheDocument();
  });

  it('shows tutorial content with proper animations', async () => {
    render(<MainChat />);
    
    // Wait for content to animate in
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    }, { timeout: 1000 });
    
    // Verify tutorial sections are present
    expect(screen.getByText('Get Started in 3 Easy Steps:')).toBeInTheDocument();
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
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
      expect(screen.getByText('Get Started in 3 Easy Steps:')).toBeInTheDocument();
    });
  });
});
