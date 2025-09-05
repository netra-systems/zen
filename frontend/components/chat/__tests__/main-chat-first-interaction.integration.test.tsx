import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MainChat from '../MainChat';

// Mock all the dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/store/threadStore');  
jest.mock('@/store/authStore');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/hooks/useLoadingState');
jest.mock('@/hooks/useEventProcessor');
jest.mock('@/hooks/useThreadNavigation');
jest.mock('@/hooks/useInitializationCoordinator');
jest.mock('@/components/chat/ChatHeader', () => {
  return function MockChatHeader() {
    return <div data-testid="chat-header">Chat Header</div>;
  };
});
jest.mock('@/components/chat/MessageList', () => {
  return function MockMessageList() {
    return <div data-testid="message-list">Message List</div>;
  };
});
jest.mock('@/components/chat/PersistentResponseCard', () => {
  return function MockPersistentResponseCard() {
    return <div data-testid="response-card">Response Card</div>;
  };
});

// Import mocked hooks
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';
import { useInitializationCoordinator } from '@/hooks/useInitializationCoordinator';

const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
const mockUseThreadStore = useThreadStore as jest.MockedFunction<typeof useThreadStore>;
const mockUseAuthStore = useAuthStore as jest.MockedFunction<typeof useAuthStore>;
const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;
const mockUseLoadingState = useLoadingState as jest.MockedFunction<typeof useLoadingState>;
const mockUseEventProcessor = useEventProcessor as jest.MockedFunction<typeof useEventProcessor>;
const mockUseThreadNavigation = useThreadNavigation as jest.MockedFunction<typeof useThreadNavigation>;
const mockUseInitializationCoordinator = useInitializationCoordinator as jest.MockedFunction<typeof useInitializationCoordinator>;

describe('MainChat First Interaction Integration', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mock returns
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn(),
      addMessage: jest.fn(),
      setProcessing: jest.fn()
    } as any);

    mockUseThreadStore.mockReturnValue({
      currentThreadId: null
    } as any);

    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true
    } as any);

    mockUseWebSocket.mockReturnValue({
      messages: [],
      sendMessage: jest.fn(),
      status: 'connected'
    } as any);

    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: true,
      loadingMessage: ''
    } as any);

    mockUseEventProcessor.mockReturnValue({
      processedCount: 0,
      queueSize: 0,
      droppedCount: 0
    } as any);

    mockUseThreadNavigation.mockReturnValue({
      currentThreadId: null,
      isNavigating: false
    } as any);

    mockUseInitializationCoordinator.mockReturnValue({
      state: { phase: 'ready', progress: 100 },
      isInitialized: true
    } as any);
  });

  it('should hide welcome message and collapse examples when user starts typing', async () => {
    const user = userEvent.setup();
    
    render(<MainChat />);
    
    // Initially should show welcome message and examples
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
    expect(screen.getByText(/Get Started in 3 Easy Steps/)).toBeInTheDocument();
    
    // Find the message input
    const messageInput = screen.getByRole('textbox');
    
    // Start typing - this should trigger the hide behavior
    await user.type(messageInput, 'H');
    
    // Wait for animations and state updates
    await waitFor(() => {
      // Welcome message should be hidden
      expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
      expect(screen.queryByText(/Get Started in 3 Easy Steps/)).not.toBeInTheDocument();
    }, { timeout: 1000 });
    
    // Examples should still be present but collapsed - the component is still there
    expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
  });

  it('should not hide content when pressing navigation keys', async () => {
    const user = userEvent.setup();
    
    render(<MainChat />);
    
    // Initially should show welcome message
    expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    
    // Find the message input
    const messageInput = screen.getByRole('textbox');
    
    // Press navigation keys - should not trigger hide
    await user.click(messageInput);
    fireEvent.keyDown(messageInput, { key: 'ArrowUp' });
    fireEvent.keyDown(messageInput, { key: 'ArrowDown' });
    fireEvent.keyDown(messageInput, { key: 'Tab' });
    
    // Welcome message should still be visible
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
  });

  it('should reset welcome state when starting new thread', async () => {
    const { rerender } = render(<MainChat />);
    
    // Mock typing to hide welcome
    const user = userEvent.setup();
    const messageInput = screen.getByRole('textbox');
    await user.type(messageInput, 'Hello');
    
    // Wait for hide
    await waitFor(() => {
      expect(screen.queryByText('Welcome to Netra AI')).not.toBeInTheDocument();
    });
    
    // Simulate new thread by updating mocks to show empty state again
    mockUseUnifiedChatStore.mockReturnValue({
      isProcessing: false,
      messages: [],
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      currentRunId: null,
      activeThreadId: null,  // No active thread
      isThreadLoading: false,
      handleWebSocketEvent: jest.fn(),
      addMessage: jest.fn(),
      setProcessing: jest.fn()
    } as any);

    mockUseThreadStore.mockReturnValue({
      currentThreadId: null  // No current thread
    } as any);
    
    // Re-render with new state
    rerender(<MainChat />);
    
    // Welcome message should be shown again for new thread
    await waitFor(() => {
      expect(screen.getByText('Welcome to Netra AI')).toBeInTheDocument();
    });
  });
});