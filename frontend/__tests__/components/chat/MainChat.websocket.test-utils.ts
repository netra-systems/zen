// Mock all hooks before any imports
var mockUseUnifiedChatStore = jest.fn();
var mockUseWebSocket = jest.fn();
var mockUseLoadingState = jest.fn();
var mockUseEventProcessor = jest.fn();

// Mock store data
export const mockStore = {
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
  setProcessing: jest.fn(),
  clearMessages: jest.fn(),
  updateLayerData: jest.fn(),
};

// Setup fetch mock for config
export const setupFetchMock = () => {
  global.fetch = jest.fn().mockResolvedValue({
    json: jest.fn().mockResolvedValue({
      ws_url: 'ws://localhost:8000/ws'
    })
  });
};

// Setup unified chat store mock
export const setupUnifiedChatMock = () => {
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
    setProcessing: jest.fn(),
    clearMessages: jest.fn(),
    updateLayerData: jest.fn(),
  });
};

// Setup WebSocket hook mock
export const setupWebSocketMock = () => {
  mockUseWebSocket.mockReturnValue({
    messages: [],
    connected: true,
    error: null
  });
};

// Setup loading state mock
export const setupLoadingStateMock = () => {
  mockUseLoadingState.mockReturnValue({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: false,
    loadingMessage: ''
  });
};

// Setup thread navigation mock
export const setupThreadNavigationMock = () => {
  const mockUseThreadNavigation = require('@/hooks/useThreadNavigation').useThreadNavigation;
  mockUseThreadNavigation.mockReturnValue({
    currentThreadId: null,
    isNavigating: false,
    navigateToThread: jest.fn(),
    createNewThread: jest.fn()
  });
};

// Setup event processor mock
export const setupEventProcessorMock = () => {
  mockUseEventProcessor.mockReturnValue({
    processedEvents: [],
    isProcessing: false,
    stats: { processed: 0, failed: 0 }
  });
};

// Main setup function
export const setupMocks = () => {
  jest.clearAllMocks();
  jest.useFakeTimers();
  setupFetchMock();
  setupUnifiedChatMock();
  setupWebSocketMock();
  setupLoadingStateMock();
  setupThreadNavigationMock();
  setupEventProcessorMock();
};

// Cleanup function
export const cleanupMocks = () => {
  jest.useRealTimers();
};

// Export mock functions for direct manipulation in tests
export {
  mockUseUnifiedChatStore,
  mockUseWebSocket,
  mockUseLoadingState,
  mockUseEventProcessor
};