/**
 * Test for initialization transition fix
 * Verifies that the loading screen properly transitions to chat when initialization completes
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import MainChat from '@/components/chat/MainChat';

// Mock the hooks
jest.mock('@/hooks/useInitializationCoordinator', () => ({
  useInitializationCoordinator: jest.fn()
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: jest.fn()
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn()
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn()
}));

jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: jest.fn()
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: jest.fn()
}));

jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn()
  }
}));

// Mock child components
jest.mock('@/components/InitializationProgress', () => ({
  InitializationProgress: ({ phase, progress }: any) => (
    <div data-testid="initialization-progress">
      Loading: {phase} - {progress}%
    </div>
  )
}));

jest.mock('@/components/chat/ChatHeader', () => ({
  __esModule: true,
  default: () => <div data-testid="chat-header">Chat Header</div>
}));

jest.mock('@/components/chat/MessageList', () => ({
  __esModule: true, 
  default: () => <div data-testid="message-list">Message List</div>
}));

jest.mock('@/components/chat/MessageInput', () => ({
  __esModule: true,
  default: React.forwardRef((props, ref) => (
    <div data-testid="message-input">Message Input</div>
  ))
}));

jest.mock('@/components/chat/ExamplePrompts', () => ({
  __esModule: true,
  default: () => <div data-testid="example-prompts">Example Prompts</div>
}));

jest.mock('@/components/chat/PersistentResponseCard', () => ({
  __esModule: true,
  default: () => <div data-testid="response-card">Response Card</div>
}));

jest.mock('@/components/chat/OverflowPanel', () => ({
  __esModule: true,
  default: () => null
}));

jest.mock('@/components/chat/EventDiagnosticsPanel', () => ({
  __esModule: true,
  default: () => null
}));

describe('MainChat Initialization Transition Fix', () => {
  const mockUseInitializationCoordinator = require('@/hooks/useInitializationCoordinator').useInitializationCoordinator;
  const mockUseLoadingState = require('@/hooks/useLoadingState').useLoadingState;
  const mockUseWebSocket = require('@/hooks/useWebSocket').useWebSocket;
  const mockUseUnifiedChatStore = require('@/store/unified-chat').useUnifiedChatStore;
  const mockUseEventProcessor = require('@/hooks/useEventProcessor').useEventProcessor;
  const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Default mock implementations
    mockUseWebSocket.mockReturnValue({
      status: 'OPEN',
      isConnected: true,
      messages: []
    });
    
    mockUseUnifiedChatStore.mockReturnValue({
      messages: [],
      isProcessing: false,
      currentRunId: null,
      activeThreadId: null,
      isThreadLoading: false,
      fastLayerData: null,
      mediumLayerData: null,
      slowLayerData: null,
      initialized: true,
      handleWebSocketEvent: jest.fn()
    });
    
    mockUseEventProcessor.mockReturnValue({
      processEvent: jest.fn()
    });
    
    mockUseThreadNavigation.mockReturnValue({
      isNavigating: false
    });
  });

  test('shows loading screen when initialization is at 100% but phase is not ready', () => {
    // Simulate stuck at 100% but not ready
    mockUseInitializationCoordinator.mockReturnValue({
      state: {
        phase: 'store',
        progress: 100,
        isReady: false,
        error: null
      },
      isInitialized: false,
      reset: jest.fn()
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: true, // This would be stuck true
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: '',
      isInitialized: false,
      loadingState: 'INITIALIZING'
    });
    
    render(<MainChat />);
    
    // Should show loading screen
    expect(screen.getByTestId('initialization-progress')).toBeInTheDocument();
    expect(screen.getByText(/Loading: store - 100%/)).toBeInTheDocument();
    expect(screen.queryByTestId('main-chat')).not.toBeInTheDocument();
  });
  
  test('transitions to chat when phase is ready even if shouldShowLoading is true', () => {
    // Simulate phase ready but shouldShowLoading stuck
    mockUseInitializationCoordinator.mockReturnValue({
      state: {
        phase: 'ready',
        progress: 100,
        isReady: true,
        error: null
      },
      isInitialized: true,
      reset: jest.fn()
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: true, // This was causing the stuck state
      shouldShowEmptyState: true,
      shouldShowExamplePrompts: false,
      loadingMessage: '',
      isInitialized: true,
      loadingState: 'READY'
    });
    
    render(<MainChat />);
    
    // Should NOT show loading screen - should show chat
    expect(screen.queryByTestId('initialization-progress')).not.toBeInTheDocument();
    expect(screen.getByTestId('main-chat')).toBeInTheDocument();
    expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
  });
  
  test('shows loading during actual initialization phases', () => {
    const phases = [
      { phase: 'auth', progress: 20 },
      { phase: 'websocket', progress: 50 },
      { phase: 'store', progress: 80 }
    ];
    
    phases.forEach(({ phase, progress }) => {
      mockUseInitializationCoordinator.mockReturnValue({
        state: {
          phase,
          progress,
          isReady: false,
          error: null
        },
        isInitialized: false,
        reset: jest.fn()
      });
      
      mockUseLoadingState.mockReturnValue({
        shouldShowLoading: true,
        shouldShowEmptyState: false,
        shouldShowExamplePrompts: false,
        loadingMessage: '',
        isInitialized: false,
        loadingState: 'INITIALIZING'
      });
      
      const { rerender } = render(<MainChat />);
      
      expect(screen.getByTestId('initialization-progress')).toBeInTheDocument();
      expect(screen.getByText(new RegExp(`Loading: ${phase} - ${progress}%`))).toBeInTheDocument();
      
      rerender(<MainChat />);
    });
  });
  
  test('handles error phase correctly', () => {
    mockUseInitializationCoordinator.mockReturnValue({
      state: {
        phase: 'error',
        progress: 0,
        isReady: false,
        error: new Error('Connection failed')
      },
      isInitialized: false,
      reset: jest.fn()
    });
    
    mockUseLoadingState.mockReturnValue({
      shouldShowLoading: false,
      shouldShowEmptyState: false,
      shouldShowExamplePrompts: false,
      loadingMessage: 'Connection failed',
      isInitialized: false,
      loadingState: 'ERROR'
    });
    
    render(<MainChat />);
    
    // Should show error in loading screen
    expect(screen.getByTestId('initialization-progress')).toBeInTheDocument();
    expect(screen.getByText(/Loading: error - 0%/)).toBeInTheDocument();
  });
});