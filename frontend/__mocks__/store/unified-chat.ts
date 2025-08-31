/**
 * Mock for unified chat store for testing
 */

let mockState: any = {
  activeThreadId: null,
  messages: [],
  isThreadLoading: false,
  threadLoadingState: null,
  setActiveThread: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
  }),
  setThreadLoading: jest.fn((isLoading) => {
    mockState.isThreadLoading = isLoading;
  }),
  startThreadLoading: jest.fn((threadId) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = true;
    mockState.messages = [];
  }),
  completeThreadLoading: jest.fn((threadId, messages) => {
    mockState.activeThreadId = threadId;
    mockState.isThreadLoading = false;
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
    getState: () => mockState
  }
);

export const resetMockState = () => {
  mockState = {
    activeThreadId: null,
    messages: [],
    isThreadLoading: false,
    threadLoadingState: null,
    setActiveThread: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
    }),
    setThreadLoading: jest.fn((isLoading) => {
      mockState.isThreadLoading = isLoading;
    }),
    startThreadLoading: jest.fn((threadId) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = true;
      mockState.messages = [];
    }),
    completeThreadLoading: jest.fn((threadId, messages) => {
      mockState.activeThreadId = threadId;
      mockState.isThreadLoading = false;
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