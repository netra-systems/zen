// Global test type definitions
import '@testing-library/jest-dom';

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
  
  namespace jest {
    interface Matchers<R> {
      toBe(expected: any): R;
      toEqual(expected: any): R;
      toContain(expected: any): R;
      toBeNull(): R;
      toHaveBeenCalled(): R;
      toHaveBeenCalledWith(...args: any[]): R;
      toHaveBeenCalledTimes(times: number): R;
      rejects: {
        toThrow(error?: any): Promise<R>;
      };
    }
  }
}

export {};