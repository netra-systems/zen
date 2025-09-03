/**
 * Mock for unified chat store for testing
 */

let mockState: any = {
  // Basic state
  activeThreadId: null,
  messages: [],
  isThreadLoading: false,
  threadLoading: false,  // Add threadLoading for compatibility
  threadLoadingState: null,
  isProcessing: false,  // Add missing isProcessing property
  initialized: true,
  isConnected: false,
  connectionError: null,
  
  // Thread management actions - create fresh mocks that update state
  setActiveThread: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
    return mockState; // Return state for chaining
  }),
  setThreadLoading: jest.fn((isLoading) => {
    mockState.isThreadLoading = isLoading;
    mockState.threadLoading = isLoading;  // Update both for compatibility
    return mockState;
  }),
  startThreadLoading: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = true;
    mockState.threadLoading = true;  // Update both for compatibility
    mockState.messages = [];
    return mockState;
  }),
  completeThreadLoading: jest.fn((threadId, messages) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = false;
    mockState.threadLoading = false;  // Update both for compatibility
    mockState.messages = messages || [];
    return mockState;
  }),
  clearMessages: jest.fn(() => {
    mockState.messages = [];
    return mockState;
  }),
  loadMessages: jest.fn((messages) => {
    mockState.messages = messages || [];
    mockState.isThreadLoading = false; // Loading complete when messages loaded
    return mockState;
  }),
  handleWebSocketEvent: jest.fn((event) => {
    // Mock processing of WebSocket events
    if (event?.type) {
      // Store the event for test verification
      if (!mockState.wsEvents) mockState.wsEvents = [];
      mockState.wsEvents.push(event);
    }
    return mockState;
  }),
  
  // Additional methods that might be called
  resetStore: jest.fn(() => {
    mockState.activeThreadId = null;
    mockState.messages = [];
    mockState.isThreadLoading = false;
    mockState.threadLoading = false;
    mockState.isProcessing = false;
    return mockState;
  }),
  setProcessing: jest.fn((isProcessing) => {
    mockState.isProcessing = isProcessing;
    return mockState;
  }),
  setConnectionStatus: jest.fn((isConnected, error) => {
    mockState.isConnected = isConnected;
    mockState.connectionError = error || null;
    return mockState;
  })
};

export const useUnifiedChatStore = Object.assign(
  (selector?: (state: any) => any) => {
    if (selector) {
      return selector(mockState);
    }
    return mockState;
  },
  {
    setState: (newState: any) => {
      if (typeof newState === 'function') {
        mockState = { ...mockState, ...newState(mockState) };
      } else {
        mockState = { ...mockState, ...newState };
      }
    },
    getState: () => mockState,
    subscribe: jest.fn((selector: any, listener: any) => {
      // Simple mock implementation - just return a function to unsubscribe
      return jest.fn();
    })
  }
);

export const resetMockState = () => {
  mockState = {
    // Basic state
    activeThreadId: null,
    messages: [],
    isThreadLoading: false,
    threadLoading: false,  // Add threadLoading for compatibility
    threadLoadingState: null,
    isProcessing: false,  // Add missing isProcessing property
    initialized: true,
    isConnected: false,
    connectionError: null,
    
    // Thread management actions - create fresh mocks that update state
    setActiveThread: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
      return mockState; // Return state for chaining
    }),
    setThreadLoading: jest.fn((isLoading) => {
      mockState.isThreadLoading = isLoading;
      mockState.threadLoading = isLoading;  // Update both for compatibility
      return mockState;
    }),
    startThreadLoading: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = true;
      mockState.threadLoading = true;  // Update both for compatibility
      mockState.messages = [];
      return mockState;
    }),
    completeThreadLoading: jest.fn((threadId, messages) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = false;
      mockState.threadLoading = false;  // Update both for compatibility
      mockState.messages = messages || [];
      return mockState;
    }),
    clearMessages: jest.fn(() => {
      mockState.messages = [];
      return mockState;
    }),
    loadMessages: jest.fn((messages) => {
      mockState.messages = messages || [];
      mockState.isThreadLoading = false; // Loading complete when messages loaded
      return mockState;
    }),
    handleWebSocketEvent: jest.fn((event) => {
      // Mock processing of WebSocket events
      if (event?.type) {
        // Store the event for test verification
        if (!mockState.wsEvents) mockState.wsEvents = [];
        mockState.wsEvents.push(event);
      }
      return mockState;
    }),
    
    // Additional methods that might be called
    resetStore: jest.fn(() => {
      mockState.activeThreadId = null;
      mockState.messages = [];
      mockState.isThreadLoading = false;
      mockState.threadLoading = false;
      mockState.isProcessing = false;
      return mockState;
    }),
    setProcessing: jest.fn((isProcessing) => {
      mockState.isProcessing = isProcessing;
      return mockState;
    }),
    setConnectionStatus: jest.fn((isConnected, error) => {
      mockState.isConnected = isConnected;
      mockState.connectionError = error || null;
      return mockState;
    })
  };
};