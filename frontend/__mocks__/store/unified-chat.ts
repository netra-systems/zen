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
  
  // Thread management actions - these MUST update the shared mockState
  setActiveThread: null as any, // Will be set below
  setThreadLoading: null as any, // Will be set below
  startThreadLoading: null as any, // Will be set below
  completeThreadLoading: null as any, // Will be set below
  clearMessages: null as any, // Will be set below
  loadMessages: null as any, // Will be set below
  handleWebSocketEvent: null as any, // Will be set below
  
  // Additional methods that might be called
  resetStore: null as any, // Will be set below
  setProcessing: null as any, // Will be set below
  setConnectionStatus: null as any, // Will be set below
};

// Initialize the mock functions that update the shared mockState
const initializeMockFunctions = (state: any) => {
  state.setActiveThread = jest.fn((threadId) => {
    state.activeThreadId = threadId;
    return state;
  });
  
  state.setThreadLoading = jest.fn((isLoading) => {
    state.isThreadLoading = isLoading;
    state.threadLoading = isLoading;
    return state;
  });
  
  state.startThreadLoading = jest.fn((threadId) => {
    state.activeThreadId = threadId;
    state.isThreadLoading = true;
    state.threadLoading = true;
    state.messages = [];
    return state;
  });
  
  state.completeThreadLoading = jest.fn((threadId, messages) => {
    state.activeThreadId = threadId;
    state.isThreadLoading = false;
    state.threadLoading = false;
    state.messages = messages || [];
    return state;
  });
  
  state.clearMessages = jest.fn(() => {
    state.messages = [];
    return state;
  });
  
  state.loadMessages = jest.fn((messages) => {
    state.messages = messages || [];
    state.isThreadLoading = false;
    return state;
  });
  
  state.handleWebSocketEvent = jest.fn((event) => {
    if (event?.type) {
      if (!state.wsEvents) state.wsEvents = [];
      state.wsEvents.push(event);
    }
    return state;
  });
  
  state.resetStore = jest.fn(() => {
    state.activeThreadId = null;
    state.messages = [];
    state.isThreadLoading = false;
    state.threadLoading = false;
    state.isProcessing = false;
    return state;
  });
  
  state.setProcessing = jest.fn((isProcessing) => {
    state.isProcessing = isProcessing;
    return state;
  });
  
  state.setConnectionStatus = jest.fn((isConnected, error) => {
    state.isConnected = isConnected;
    state.connectionError = error || null;
    return state;
  });
};

// Initialize the functions for the initial mockState
initializeMockFunctions(mockState);

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
    
    // Thread management actions - placeholders to be initialized
    setActiveThread: null as any,
    setThreadLoading: null as any,
    startThreadLoading: null as any,
    completeThreadLoading: null as any,
    clearMessages: null as any,
    loadMessages: null as any,
    handleWebSocketEvent: null as any,
    resetStore: null as any,
    setProcessing: null as any,
    setConnectionStatus: null as any,
  };
  
  // Initialize the mock functions with the new state reference
  initializeMockFunctions(mockState);
};