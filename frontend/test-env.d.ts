/**
 * Test Environment Type Definitions
 * Ensures Jest and testing library types are properly available
 */

/// <reference types="jest" />
/// <reference types="@testing-library/jest-dom" />

// Force Jest globals to be available
declare global {
  const expect: jest.Expect;
  const test: jest.It;
  const it: jest.It;
  const describe: jest.Describe;
  const beforeAll: jest.Lifecycle;
  const beforeEach: jest.Lifecycle;
  const afterAll: jest.Lifecycle;
  const afterEach: jest.Lifecycle;
  const jest: Jest;
}

// Override Jest expect interface to fix matcher issues
declare namespace jest {
  interface Matchers<R> {
    toBe(expected: any): R;
    toEqual(expected: any): R;
    toStrictEqual(expected: any): R;
    toContain(expected: any): R;
    toBeNull(): R;
    toBeUndefined(): R;
    toBeDefined(): R;
    toBeTruthy(): R;
    toBeFalsy(): R;
    toHaveBeenCalled(): R;
    toHaveBeenCalledWith(...args: any[]): R;
    toHaveBeenCalledTimes(expected: number): R;
    toThrow(expected?: any): R;
    rejects: {
      toThrow(expected?: any): Promise<R>;
    };
    resolves: {
      toBe(expected: any): Promise<R>;
      toEqual(expected: any): Promise<R>;
    };
  }
}

export {};