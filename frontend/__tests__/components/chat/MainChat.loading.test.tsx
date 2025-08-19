/**
 * Test suite for MainChat loading states
 * Tests that the chat UI shows correct content based on loading conditions
 * 
 * @compliance testing.xml - Component integration testing
 * @prevents websocket-loading-state-transitions regression
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { ChatLoadingState } from '@/types/loading-state';

// Mock all dependencies
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn()
}));
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn()
}));
jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn()
}));
jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: jest.fn()
}));
// Mock utility services but NOT UI components  
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
}));

describe('MainChat Loading States', () => {
  const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
  const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
  const mockUseLoadingState = useLoadingState as jest.MockedFunction<typeof useLoadingState>;
  const mockUseEventProcessor = useEventProcessor as jest.MockedFunction<typeof useEventProcessor>;
  const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation as jest.MockedFunction<any>;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock for event processor
    mockUseEventProcessor.mockReturnValue({
      processEvent: jest.fn(),
      getQueueSize: jest.fn(() => 0),
      getProcessedCount: jest.fn(() => 0),
      getDroppedCount: jest.fn(() => 0),
      getDuplicateCount: jest.fn(() => 0),
      getAverageProcessingTime: jest.fn(() => 0),
      getLastProcessedTime: jest.fn(() => null),
      reset: jest.fn(),
      getMetrics: jest.fn(() => ({
        queueSize: 0,
        processedCount: 0,
        droppedCount: 0,
        duplicateCount: 0,
        averageProcessingTime: 0,
        lastProcessedTime: null
      }))
    } as any);

    // Default mock for WebSocket
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    // Default mock for Thread Navigation
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false,
      navigateToThread: jest.fn(),
      createNewThread: jest.fn()
    });

    // Default mock for store
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
    } as any);
  });

  /**
   * Test Case 1: Should show loading spinner when initializing
   * This verifies the "Loading chat..." state that was stuck before the fix
   */
  it('should show loading spinner with "Loading chat..." when initializing', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.INITIALIZING,
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Loading chat...',
      isInitialized: false
    });

    render(<MainChat />);

    // Should show loading spinner
    expect(screen.getByText('Loading chat...')).toBeInTheDocument();
    // Should not show other components
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 2: Should show example prompts for new thread (no messages)
   * This is the state that should appear after the fix when thread is ready with no messages
   */
  it('should show example prompts when thread is ready with no messages', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.THREAD_READY,
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true,
      loadingMessage: 'Thread ready',
      isInitialized: true
    });

    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    } as any);

    render(<MainChat />);

    // Should show main UI components
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    
    // Should not show loading
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    // Message list might be rendered but empty - that's OK
  });

  /**
   * Test Case 3: Should show empty state when no thread selected
   */
  it('should show empty state when connected but no thread selected', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.READY,
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Ready',
      isInitialized: true
    });

    render(<MainChat />);

    // Should show welcome message
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    expect(screen.getByText(/Create a new conversation/)).toBeInTheDocument();
    
    // Should show main UI components
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    
    // Should not show loading or example prompts
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 4: Should show message list when thread has messages
   */
  it('should show message list when thread has messages', () => {
    // First set up the store with messages
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [
        { id: '1', content: 'Hello', role: 'user' },
        { id: '2', content: 'Hi there!', role: 'assistant' }
      ],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    } as any);

    // Mock thread navigation (not navigating)
    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: 'thread_123',
      isNavigating: false,
      navigateToThread: jest.fn(),
      createNewThread: jest.fn()
    });

    // Then mock loading state for thread with messages (no loading, no example prompts)
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.THREAD_READY,
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Thread ready',
      isInitialized: true
    });

    render(<MainChat />);

    // Should show message list
    expect(screen.getByRole('list')).toBeInTheDocument();
    
    // Should not show loading or example prompts
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 5: Should show loading when switching threads
   */
  it('should show thread loading indicator when switching threads', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.LOADING_THREAD,
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Loading thread messages...',
      isInitialized: true
    });

    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread_456',
      isThreadLoading: true,
      handleWebSocketEvent: jest.fn()
    } as any);

    render(<MainChat />);

    // Should show loading state
    expect(screen.getByText('Loading thread messages...')).toBeInTheDocument();
    
    // Should not show other content
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 6: Should show processing state when agent is running
   */
  it('should show response card when processing', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.PROCESSING,
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Processing with triage...',
      isInitialized: true
    });

    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: true,
      messages: [{ id: '1', content: 'Analyze this', role: 'user' }],
      fastLayerData: { agentName: 'triage', status: 'running' },
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: 'run_123',
      activeThreadId: 'thread_123',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    } as any);

    render(<MainChat />);

    // Should show response card for processing
    expect(screen.getByText(/response card/i)).toBeInTheDocument();
    
    // Should also show message list
    expect(screen.getByRole('list')).toBeInTheDocument();
    
    // Should not show loading spinner
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
  });

  /**
   * Test Case 7: Should handle connection failure gracefully
   */
  it('should show connection failed message', () => {
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.CONNECTION_FAILED,
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Connection failed. Retrying...',
      isInitialized: true
    });

    render(<MainChat />);

    expect(screen.getByText('Connection failed. Retrying...')).toBeInTheDocument();
  });

  /**
   * Test Case 8: Should transition from loading to ready state
   */
  it('should transition from loading to ready state correctly', async () => {
    const { rerender } = render(<MainChat />);

    // Start with loading state
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.INITIALIZING,
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Loading chat...',
      isInitialized: false
    });

    rerender(<MainChat />);
    expect(screen.getByText('Loading chat...')).toBeInTheDocument();

    // Transition to ready state
    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.THREAD_READY,
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true,
      loadingMessage: 'Thread ready',
      isInitialized: true
    });

    rerender(<MainChat />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
      expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    });
  });

  /**
   * Test Case 9: Should handle rapid state changes without breaking UI
   */
  it('should handle rapid state changes gracefully', () => {
    const { rerender } = render(<MainChat />);

    const states = [
      {
        loadingState: ChatLoadingState.INITIALIZING,
        shouldShowLoading: true,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: 'Loading chat...',
        isInitialized: false
      },
      {
        loadingState: ChatLoadingState.CONNECTING,
        shouldShowLoading: true,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: 'Connecting to chat service...',
        isInitialized: true
      },
      {
        loadingState: ChatLoadingState.THREAD_READY,
        shouldShowLoading: false,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: true,
        loadingMessage: 'Thread ready',
        isInitialized: true
      }
    ];

    // Should not throw during rapid state changes
    states.forEach(state => {
      mockUseLoadingState.mockReturnValue(state);
      expect(() => rerender(<MainChat />)).not.toThrow();
    });

    // Final state should be correct
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
  });

  /**
   * Test Case 10: Should show correct UI for hot-reload scenario
   * This specifically tests the scenario that caused the original bug
   */
  it('should handle hot-reload with pre-connected WebSocket correctly', () => {
    // Simulate hot-reload scenario: WebSocket already connected, thread exists
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      messages: [],
      sendMessage: jest.fn()
    });

    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: 'thread_hot_reload',
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn()
    } as any);

    mockUseLoadingState.mockReturnValue({
      loadingState: ChatLoadingState.THREAD_READY,
      shouldShowLoading: false, // This was incorrectly true before the fix
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true,
      loadingMessage: 'Thread ready',
      isInitialized: true
    });

    render(<MainChat />);

    // Should NOT show loading (this was the bug)
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    
    // Should show example prompts for empty thread
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    
    // Should show all UI components
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});