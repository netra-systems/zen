/**
 * MainChat Loading Test Utilities
 * Shared mocks and helpers for MainChat loading state tests
 * 
 * @compliance conventions.xml - Under 300 lines, 8 lines per function
 */

import { ChatLoadingState } from '@/types/loading-state';

// Mock setup helpers (8 lines max each)
export const createMockEventProcessor = () => ({
  processEvent: jest.fn(),
  getQueueSize: jest.fn(() => 0),
  getProcessedCount: jest.fn(() => 0),
  getDroppedCount: jest.fn(() => 0),
  getDuplicateCount: jest.fn(() => 0),
  getAverageProcessingTime: jest.fn(() => 0),
  getLastProcessedTime: jest.fn(() => null),
  reset: jest.fn()
});

export const createMockEventProcessorWithMetrics = () => ({
  ...createMockEventProcessor(),
  getMetrics: jest.fn(() => ({
    queueSize: 0,
    processedCount: 0,
    droppedCount: 0,
    duplicateCount: 0,
    averageProcessingTime: 0,
    lastProcessedTime: null
  }))
});

export const createMockWebSocket = () => ({
  status: 'OPEN' as const,
  messages: [],
  sendMessage: jest.fn()
});

export const createMockThreadNavigation = () => ({
  currentThreadId: null,
  isNavigating: false,
  navigateToThread: jest.fn(),
  createNewThread: jest.fn()
});

export const createMockChatStore = (overrides = {}) => ({
  isProcessing: false,
  messages: [],
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  currentRunId: null,
  activeThreadId: null,
  isThreadLoading: false,
  handleWebSocketEvent: jest.fn(),
  ...overrides
});

// Loading state factory helpers (8 lines max each)
export const createInitializingState = () => ({
  loadingState: ChatLoadingState.INITIALIZING,
  shouldShowLoading: true,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: 'Loading chat...',
  isInitialized: false
});

export const createThreadReadyState = () => ({
  loadingState: ChatLoadingState.THREAD_READY,
  shouldShowLoading: false,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: true,
  loadingMessage: 'Thread ready',
  isInitialized: true
});

export const createEmptyState = () => ({
  loadingState: ChatLoadingState.READY,
  shouldShowLoading: false,
  shouldShowEmptyState: true,
  shouldShowExamplePrompts: false,
  loadingMessage: 'Ready',
  isInitialized: true
});

export const createProcessingState = () => ({
  loadingState: ChatLoadingState.PROCESSING,
  shouldShowLoading: false,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: 'Processing with triage...',
  isInitialized: true
});

export const createConnectionFailedState = () => ({
  loadingState: ChatLoadingState.CONNECTION_FAILED,
  shouldShowLoading: true,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: 'Connection failed. Retrying...',
  isInitialized: true
});

export const createLoadingThreadState = () => ({
  loadingState: ChatLoadingState.LOADING_THREAD,
  shouldShowLoading: true,
  shouldShowEmptyState: false,
  shouldShowExamplePrompts: false,
  loadingMessage: 'Loading thread messages...',
  isInitialized: true
});

// Mock setup function
export const setupLoadingTestMocks = (
  mockUseLoadingState: jest.MockedFunction<any>,
  mockUseWebSocket: jest.MockedFunction<any>,
  mockUseEventProcessor: jest.MockedFunction<any>,
  mockUseThreadNavigation: jest.MockedFunction<any>,
  mockUseUnifiedChatStore: jest.MockedFunction<any>
) => {
  mockUseEventProcessor.mockReturnValue(createMockEventProcessorWithMetrics());
  mockUseWebSocket.mockReturnValue(createMockWebSocket());
  mockUseThreadNavigation.mockReturnValue(createMockThreadNavigation());
  mockUseUnifiedChatStore.mockReturnValue(createMockChatStore());
};