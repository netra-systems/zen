// Global test type definitions
/// <reference types="jest" />
/// <reference types="@testing-library/jest-dom" />

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