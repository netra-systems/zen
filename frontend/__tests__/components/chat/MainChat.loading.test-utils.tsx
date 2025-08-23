/**
 * MainChat Loading Test Utils
 * Helper utilities for testing MainChat loading states and transitions
 * 
 * @compliance testing.xml - Test utility helpers for loading states
 * @compliance conventions.xml - Under 300 lines, functions ≤8 lines
 */

import { ChatLoadingState } from '@/types/loading-state';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface MockLoadingState {
  loadingState: ChatLoadingState;
  shouldShowLoading: boolean;
  shouldShowEmptyState: boolean;
  shouldShowExamplePrompts: boolean;
  loadingMessage: string;
  isInitialized: boolean;
}

export interface MockChatStoreConfig {
  messages?: Array<{ id: string; content: string; role: string }>;
  isProcessing?: boolean;
  activeThreadId?: string | null;
  isThreadLoading?: boolean;
  fastLayerData?: { agentName: string; status: string };
  currentRunId?: string | null;
}

// ============================================================================
// LOADING STATE FACTORIES
// ============================================================================

/**
 * Create initializing state for testing
 */
export function createInitializingState(): MockLoadingState {
  return {
    loadingState: ChatLoadingState.INITIALIZING,
    shouldShowLoading: true,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Loading chat...',
    isInitialized: false
  };
}

/**
 * Create thread ready state for testing
 */
export function createThreadReadyState(): MockLoadingState {
  return {
    loadingState: ChatLoadingState.THREAD_READY,
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: 'Thread ready',
    isInitialized: true
  };
}

/**
 * Create loading thread state for testing
 */
export function createLoadingThreadState(): MockLoadingState {
  return {
    loadingState: ChatLoadingState.LOADING_THREAD,
    shouldShowLoading: true,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Loading thread messages...',
    isInitialized: true
  };
}

/**
 * Create processing state for testing
 */
export function createProcessingState(): MockLoadingState {
  return {
    loadingState: ChatLoadingState.PROCESSING,
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Processing...',
    isInitialized: true
  };
}

/**
 * Create connection failed state for testing
 */
export function createConnectionFailedState(): MockLoadingState {
  return {
    loadingState: ChatLoadingState.CONNECTION_FAILED,
    shouldShowLoading: true,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: 'Connection failed. Retrying...',
    isInitialized: true
  };
}

// ============================================================================
// MOCK STORE FACTORIES
// ============================================================================

/**
 * Create mock chat store with configurable options
 */
export function createMockChatStore(config: MockChatStoreConfig = {}) {
  return {
    messages: config.messages || [],
    isProcessing: config.isProcessing || false,
    activeThreadId: config.activeThreadId || null,
    isThreadLoading: config.isThreadLoading || false,
    fastLayerData: config.fastLayerData || null,
    currentRunId: config.currentRunId || null,
    addMessage: jest.fn(),
    setProcessing: jest.fn(),
    clearMessages: jest.fn()
  };
}

// ============================================================================
// MOCK SETUP FUNCTIONS
// ============================================================================

/**
 * Setup loading test mocks for all hooks
 */
export function setupLoadingTestMocks(
  mockUseLoadingState: jest.MockedFunction<any>,
  mockUseWebSocket: jest.MockedFunction<any>,
  mockUseEventProcessor: jest.MockedFunction<any>,
  mockUseThreadNavigation: jest.MockedFunction<any>,
  mockUseUnifiedChatStore: jest.MockedFunction<any>
): void {
  // Setup default loading state
  mockUseLoadingState.mockReturnValue(createInitializingState());
  
  // Setup default WebSocket mock
  mockUseWebSocket.mockReturnValue({
    sendMessage: jest.fn(),
    isConnected: true,
    status: 'OPEN'
  });
  
  // Setup default event processor
  mockUseEventProcessor.mockReturnValue({
    processEvent: jest.fn()
  });
  
  // Setup default thread navigation
  mockUseThreadNavigation.mockReturnValue({
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
  });
  
  // Setup default chat store
  mockUseUnifiedChatStore.mockReturnValue(createMockChatStore());
}

/**
 * Reset all test mocks to clean state
 */
export function resetLoadingTestMocks(): void {
  jest.clearAllMocks();
}

/**
 * Setup clean test environment for loading tests
 */
export function setupCleanLoadingTestState(): void {
  resetLoadingTestMocks();
  
  // Mock console to reduce noise
  global.console.warn = jest.fn();
  global.console.error = jest.fn();
  
  // Mock ResizeObserver
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}