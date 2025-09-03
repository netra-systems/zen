/**
 * Mock for unified chat store for testing
 */

let mockState: any = {
  activeThreadId: null,
  messages: [],
  isThreadLoading: false,
  threadLoading: false,  // Add threadLoading for compatibility
  threadLoadingState: null,
  setActiveThread: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
  }),
  setThreadLoading: jest.fn((isLoading) => {
    mockState.isThreadLoading = isLoading;
    mockState.threadLoading = isLoading;  // Update both for compatibility
  }),
  startThreadLoading: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = true;
    mockState.threadLoading = true;  // Update both for compatibility
    mockState.messages = [];
  }),
  completeThreadLoading: jest.fn((threadId, messages) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = false;
    mockState.threadLoading = false;  // Update both for compatibility
    mockState.messages = messages;
  }),
  clearMessages: jest.fn(() => {
    mockState.messages = [];
  }),
  loadMessages: jest.fn((messages) => {
    mockState.messages = messages;
  }),
  handleWebSocketEvent: jest.fn()
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
    activeThreadId: null,
    messages: [],
    isThreadLoading: false,
    threadLoading: false,  // Add threadLoading for compatibility
    threadLoadingState: null,
    setActiveThread: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
    }),
    setThreadLoading: jest.fn((isLoading) => {
      mockState.isThreadLoading = isLoading;
      mockState.threadLoading = isLoading;  // Update both for compatibility
    }),
    startThreadLoading: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = true;
      mockState.threadLoading = true;  // Update both for compatibility
      mockState.messages = [];
    }),
    completeThreadLoading: jest.fn((threadId, messages) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = false;
      mockState.threadLoading = false;  // Update both for compatibility
      mockState.messages = messages;
    }),
    clearMessages: jest.fn(() => {
      mockState.messages = [];
    }),
    loadMessages: jest.fn((messages) => {
      mockState.messages = messages;
    }),
    handleWebSocketEvent: jest.fn()
  };
};