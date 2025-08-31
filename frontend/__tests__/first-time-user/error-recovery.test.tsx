/**
 * First-time user error recovery and resilience tests
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

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn()
  }
}));

// Import component after mocks
import MainChat from '@/components/chat/MainChat';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

describe('First-Time User Error Recovery', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('gracefully handles loading errors and shows fallback content', async () => {
    // Simulate loading error state
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: 'Connection error'
    });
    
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
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    });
    
    render(<MainChat />);
    
    // Should still show welcome content even with errors
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
    
    // User can still interact
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });

  it('maintains functionality during processing errors', async () => {
    // Simulate processing error state
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [{ id: '1', content: 'Test message', role: 'user', error: true }],
      fastLayerData: { error: 'Processing failed' },
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: 'run-123',
      activeThreadId: 'thread-1',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseWebSocket.mockReturnValue({
      messages: []
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: ''
    });
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: 'thread-1',
      isNavigating: false
    });
    
    render(<MainChat />);
    
    // Should show error in response card but keep interface functional
    await waitFor(() => {
      expect(screen.getByTestId('response-card')).toBeInTheDocument();
    });
    
    // User can still send new messages
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });

  it('shows appropriate loading states during recovery', async () => {
    // Simulate recovery loading
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Reconnecting...'
    });
    
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
    
    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0
    });
    
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    });
    
    render(<MainChat />);
    
    // Should show loading state with reconnection message
    await waitFor(() => {
      expect(screen.getByText('Reconnecting...')).toBeInTheDocument();
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});
