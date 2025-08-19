/**
 * MainChat Loading State Transitions Tests
 * Tests complex state transitions and processing states
 * 
 * @compliance testing.xml - Component integration testing
 * @compliance conventions.xml - Under 300 lines, 8 lines per function
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
import {
  createInitializingState,
  createThreadReadyState,
  createLoadingThreadState,
  createProcessingState,
  createConnectionFailedState,
  createMockChatStore,
  setupLoadingTestMocks
} from './MainChat.loading.test-utils';

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
jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
}));

describe('MainChat Loading State Transitions', () => {
  const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
  const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
  const mockUseLoadingState = useLoadingState as jest.MockedFunction<typeof useLoadingState>;
  const mockUseEventProcessor = useEventProcessor as jest.MockedFunction<typeof useEventProcessor>;
  const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation as jest.MockedFunction<any>;

  beforeEach(() => {
    jest.clearAllMocks();
    setupLoadingTestMocks(
      mockUseLoadingState,
      mockUseWebSocket,
      mockUseEventProcessor,
      mockUseThreadNavigation,
      mockUseUnifiedChatStore
    );
  });

  /**
   * Test Case 1: Should show loading when switching threads
   */
  it('should show thread loading indicator when switching threads', () => {
    mockUseLoadingState.mockReturnValue(createLoadingThreadState());
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore({
      activeThreadId: 'thread_456',
      isThreadLoading: true
    }));

    render(<MainChat />);

    expect(screen.getByText('Loading thread messages...')).toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 2: Should show processing state when agent is running
   */
  it('should show response card when processing', () => {
    mockUseLoadingState.mockReturnValue(createProcessingState());
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore({
      isProcessing: true,
      messages: [{ id: '1', content: 'Analyze this', role: 'user' }],
      fastLayerData: { agentName: 'triage', status: 'running' },
      currentRunId: 'run_123',
      activeThreadId: 'thread_123'
    }));

    render(<MainChat />);

    expect(screen.getByText(/response card/i)).toBeInTheDocument();
    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
  });

  /**
   * Test Case 3: Should handle connection failure gracefully
   */
  it('should show connection failed message', () => {
    mockUseLoadingState.mockReturnValue(createConnectionFailedState());

    render(<MainChat />);

    expect(screen.getByText('Connection failed. Retrying...')).toBeInTheDocument();
  });

  /**
   * Test Case 4: Should transition from loading to ready state
   */
  it('should transition from loading to ready state correctly', async () => {
    const { rerender } = render(<MainChat />);

    mockUseLoadingState.mockReturnValue(createInitializingState());
    rerender(<MainChat />);
    expect(screen.getByText('Loading chat...')).toBeInTheDocument();

    mockUseLoadingState.mockReturnValue(createThreadReadyState());
    rerender(<MainChat />);

    await waitFor(() => {
      expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
      expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    });
  });

  /**
   * Test Case 5: Should handle rapid state changes without breaking UI
   */
  it('should handle rapid state changes gracefully', () => {
    const { rerender } = render(<MainChat />);

    const states = [
      createInitializingState(),
      {
        loadingState: ChatLoadingState.CONNECTING,
        shouldShowLoading: true,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: 'Connecting to chat service...',
        isInitialized: true
      },
      createThreadReadyState()
    ];

    states.forEach(state => {
      mockUseLoadingState.mockReturnValue(state);
      expect(() => rerender(<MainChat />)).not.toThrow();
    });

    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
  });
});