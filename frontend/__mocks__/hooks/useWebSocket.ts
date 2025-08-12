// Mock for useWebSocket hook
export const mockSendMessage = jest.fn();
export const mockWebSocketValue = {
  sendMessage: mockSendMessage,
  status: 'OPEN' as const,
  messages: [],
};

export const useWebSocket = jest.fn(() => mockWebSocketValue);

// Allow resetting mock between tests
export const resetWebSocketMock = () => {
  mockSendMessage.mockClear();
  useWebSocket.mockClear();
  useWebSocket.mockReturnValue(mockWebSocketValue);
};