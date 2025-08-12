// Global test type definitions
declare global {
  var mockWebSocket: {
    send: jest.Mock;
    close: jest.Mock;
    addEventListener: jest.Mock;
    removeEventListener: jest.Mock;
    readyState: number;
    simulateMessage: jest.Mock;
    simulateError: jest.Mock;
    simulateReconnect: jest.Mock;
  };
}

export {};