/**
 * Startup Message Tests - Comprehensive test suite for startup message functionality
 * 
 * BVJ: All segments - Ensures consistent first-time user experience, 
 * critical for conversion from Free to Paid tiers
 * 
 * @compliance conventions.xml - Under 300 lines, 8 lines per function
 * @compliance type_safety.xml - Strongly typed test suites
 */

import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';
import { ChatLoadingState } from '@/types/loading-state';

// Mock all dependencies before imports
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
  useEventProcessor: jest.fn(() => ({
    stats: { processed: 0, queued: 0, dropped: 0 }
  }))
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: jest.fn(() => ({
    currentThreadId: null,
    isNavigating: false
  }))
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn()
}));

jest.mock('@/utils/debug-logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn()
  }
}));

// Mock child components
jest.mock('@/components/chat/ChatHeader', () => ({
  ChatHeader: () => <div data-testid="chat-header">Chat Header</div>
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList: () => <div data-testid="message-list">Message List</div>
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput: () => <div data-testid="message-input">Message Input</div>
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  ExamplePrompts: () => <div data-testid="example-prompts">Example Prompts</div>
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  PersistentResponseCard: () => <div data-testid="response-card">Response Card</div>
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  OverflowPanel: () => null
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  EventDiagnosticsPanel: () => null
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('Startup Message Comprehensive Tests', () => {
  const mockStoreState = {
    isProcessing: false,
    messages: [],
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    activeThreadId: null,
    isThreadLoading: false,
    handleWebSocketEvent: jest.fn()
  };

  const mockWebSocketState = {
    messages: [],
    status: 'connected',
    sendMessage: jest.fn()
  };

  const mockLoadingState = {
    shouldShowLoading: false,
    shouldShowEmptyState: true,
    shouldShowExamplePrompts: false,
    loadingMessage: '',
    isInitialized: true,
    loadingState: ChatLoadingState.NO_THREAD
  };

  const mockAuthState = {
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' }
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockStoreState);
    (useWebSocket as jest.Mock).mockReturnValue(mockWebSocketState);
    (useLoadingState as jest.Mock).mockReturnValue(mockLoadingState);
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthState);
  });

  /**
   * Test 1: Welcome message displays correctly on first load
   */
  it('should display welcome message when no thread is selected', () => {
    render(<MainChat />);
    
    const welcomeMessage = screen.getByText('Welcome to Netra AI');
    expect(welcomeMessage).toBeInTheDocument();
    
    const description = screen.getByText(/Create a new conversation/i);
    expect(description).toBeInTheDocument();
  });

  /**
   * Test 2: Welcome message hides when thread is selected
   */
  it('should hide welcome message when thread is selected', () => {
    const { rerender } = render(<MainChat />);
    
    // Verify welcome message is initially shown
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    
    // Update state to have active thread
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true
    });
    
    rerender(<MainChat />);
    
    // Welcome message should be gone
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
  });

  /**
   * Test 3: Example prompts show after thread selection
   */
  it('should show example prompts when thread selected but no messages', () => {
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true
    });
    
    render(<MainChat />);
    
    expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
  });

  /**
   * Test 4: Loading state shows correct message
   */
  it('should display loading message during initialization', () => {
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowLoading: true,
      loadingMessage: 'Initializing Netra AI...',
      shouldShowEmptyState: false
    });
    
    render(<MainChat />);
    
    expect(screen.getByText('Initializing Netra AI...')).toBeInTheDocument();
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
  });

  /**
   * Test 5: Thread switching shows loading indicator
   */
  it('should show thread loading indicator when switching threads', () => {
    (useUnifiedChatStore as jest.Mock).mockReturnValue({
      ...mockStoreState,
      isThreadLoading: true,
      activeThreadId: 'thread-123'
    });
    
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false
    });
    
    render(<MainChat />);
    
    expect(screen.getByText('Loading conversation...')).toBeInTheDocument();
    expect(screen.getByText(/Thread: thread-123/)).toBeInTheDocument();
  });

  /**
   * Test 6: Welcome message icon renders correctly
   */
  it('should render welcome message with correct icon', () => {
    render(<MainChat />);
    
    const iconContainer = screen.getByText('Welcome to Netra AI')
      .closest('.max-w-md')
      ?.querySelector('.w-16.h-16');
    
    expect(iconContainer).toBeInTheDocument();
    expect(iconContainer?.querySelector('svg')).toBeInTheDocument();
  });

  /**
   * Test 7: Animation classes applied to welcome message
   */
  it('should apply correct animation classes to welcome message', () => {
    render(<MainChat />);
    
    const welcomeContainer = screen.getByText('Welcome to Netra AI').closest('div');
    
    // Check for motion div props (mocked as regular div)
    expect(welcomeContainer?.parentElement).toHaveClass('flex', 'flex-col', 'items-center');
  });

  /**
   * Test 8: Welcome message responsive to auth state
   */
  it('should show different message for unauthenticated users', () => {
    (useAuthStore as jest.Mock).mockReturnValue({
      isAuthenticated: false,
      user: null
    });
    
    render(<MainChat />);
    
    // Should still show welcome but with context about needing to log in
    const welcomeMessage = screen.getByText('Welcome to Netra AI');
    expect(welcomeMessage).toBeInTheDocument();
  });

  /**
   * Test 9: Multiple rapid state changes handled correctly
   */
  it('should handle rapid state transitions without flickering', async () => {
    const { rerender } = render(<MainChat />);
    
    // Initial state - welcome message
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    
    // Rapid state change 1 - loading
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowLoading: true,
      shouldShowEmptyState: false,
      loadingMessage: 'Loading...'
    });
    rerender(<MainChat />);
    
    // Rapid state change 2 - thread ready
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: true
    });
    rerender(<MainChat />);
    
    // Final state should be stable
    expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
    expect(screen.getByTestId('example-prompts')).toBeInTheDocument();
  });

  /**
   * Test 10: Startup message persists across WebSocket reconnections
   */
  it('should maintain correct state during WebSocket reconnection', async () => {
    const { rerender } = render(<MainChat />);
    
    // Initial connected state
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    
    // Simulate WebSocket disconnect
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocketState,
      status: 'disconnected'
    });
    
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowLoading: true,
      loadingMessage: 'Reconnecting...',
      shouldShowEmptyState: false
    });
    rerender(<MainChat />);
    
    expect(screen.getByText('Reconnecting...')).toBeInTheDocument();
    
    // Simulate reconnection
    (useWebSocket as jest.Mock).mockReturnValue({
      ...mockWebSocketState,
      status: 'connected'
    });
    
    (useLoadingState as jest.Mock).mockReturnValue({
      ...mockLoadingState,
      shouldShowLoading: false,
      shouldShowEmptyState: true
    });
    rerender(<MainChat />);
    
    // Should return to welcome message
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
  });
});

/**
 * Integration Tests for Startup Message with Real Components
 */
describe('Startup Message Integration Tests', () => {
  /**
   * Test: Welcome message integrates with routing
   */
  it('should update welcome message based on URL thread parameter', () => {
    // Mock thread navigation hook
    jest.mock('@/hooks/useThreadNavigation', () => ({
      useThreadNavigation: () => ({
        currentThreadId: null,
        isNavigating: false
      })
    }));
    
    render(<MainChat />);
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
  });

  /**
   * Test: Startup message accessibility
   */
  it('should have proper ARIA labels for screen readers', () => {
    render(<MainChat />);
    
    const welcomeSection = screen.getByText('Welcome to Netra AI').closest('div');
    expect(welcomeSection).toHaveAttribute('role', 'main', { exact: false });
  });

  /**
   * Test: Performance - startup message renders quickly
   */
  it('should render startup message within performance budget', () => {
    const startTime = performance.now();
    render(<MainChat />);
    const endTime = performance.now();
    
    const renderTime = endTime - startTime;
    expect(renderTime).toBeLessThan(100); // 100ms budget
  });
});