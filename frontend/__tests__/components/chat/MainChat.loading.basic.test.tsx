/**
 * MainChat Basic Loading States Tests
 * Tests fundamental loading states and UI visibility
 * 
 * @compliance testing.xml - Component integration testing
 * @compliance conventions.xml - Under 300 lines, 8 lines per function
 * @prevents websocket-loading-state-transitions regression
 */

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import {
  createInitializingState,
  createThreadReadyState,
  createEmptyState,
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

// Mock additional required hooks
jest.mock('@/hooks/useMCPTools', () => ({
  useMCPTools: jest.fn(() => ({
    tools: [],
    servers: [],
    executions: [],
    isLoading: false,
    error: null,
    refreshTools: jest.fn()
  }))
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    user: { id: 'test', name: 'Test User' },
    token: 'test-token'
  }))
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'test-thread',
    threads: [],
    isLoading: false
  }))
}));

describe('MainChat Basic Loading States', () => {
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
   * Test Case 1: Should show loading spinner when initializing
   * This verifies the "Loading chat..." state that was stuck before the fix
   */
  it('should show loading spinner with "Loading chat..." when initializing', () => {
    mockUseLoadingState.mockReturnValue(createInitializingState());

    render(<MainChat />);

    expect(screen.getByText('Loading chat...')).toBeInTheDocument();
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('list')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 2: Should show example prompts for new thread (no messages)
   * This is the state that should appear after the fix when thread is ready
   */
  it('should show example prompts when thread is ready with no messages', async () => {
    mockUseLoadingState.mockReturnValue(createThreadReadyState());
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore({
      activeThreadId: 'thread_123'
    }));

    await act(async () => {
      render(<MainChat />);
    });

    // Check for the ExamplePrompts component heading instead of generic banner
    expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
  });

  /**
   * Test Case 3: Should show empty state when no thread selected
   */
  it('should show empty state when connected but no thread selected', async () => {
    mockUseLoadingState.mockReturnValue(createEmptyState());

    await act(async () => {
      render(<MainChat />);
    });

    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    expect(screen.getByText(/Create a new conversation/)).toBeInTheDocument();
    // Check for the main chat header instead of generic banner
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 4: Should show message list when thread has messages
   */
  it('should show message list when thread has messages', async () => {
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore({
      messages: [
        { id: '1', content: 'Hello', role: 'user' },
        { id: '2', content: 'Hi there!', role: 'assistant' }
      ],
      activeThreadId: 'thread_123'
    }));

    mockUseLoadingState.mockReturnValue(createThreadReadyState());

    await act(async () => {
      render(<MainChat />);
    });

    expect(screen.getByRole('list')).toBeInTheDocument();
    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.queryByText(/explore these examples/i)).not.toBeInTheDocument();
  });

  /**
   * Test Case 5: Should handle hot-reload scenario correctly
   * This specifically tests the scenario that caused the original bug
   */
  it('should handle hot-reload with pre-connected WebSocket correctly', async () => {
    mockUseUnifiedChatStore.mockReturnValue(createMockChatStore({
      activeThreadId: 'thread_hot_reload'
    }));

    mockUseLoadingState.mockReturnValue(createThreadReadyState());

    await act(async () => {
      render(<MainChat />);
    });

    expect(screen.queryByText('Loading chat...')).not.toBeInTheDocument();
    expect(screen.getByText(/explore these examples/i)).toBeInTheDocument();
    // Check for the chat header text instead of generic banner
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });
});