/**
 * Jest Setup Type Definitions
 * Comprehensive Jest type augmentation for all test files
 */

import '@testing-library/jest-dom';

declare global {
  var expect: jest.Expect;
  var test: jest.It;
  var it: jest.It;
  var describe: jest.Describe;
  var beforeAll: jest.Lifecycle;
  var beforeEach: jest.Lifecycle;
  var afterAll: jest.Lifecycle;
  var afterEach: jest.Lifecycle;
  var jest: Jest;

  namespace jest {
    interface Matchers<R> {
      // Core Jest matchers
      toBe(expected: any): R;
      toEqual(expected: any): R;
      toStrictEqual(expected: any): R;
      toBeCloseTo(expected: number, precision?: number): R;
      toContain(expected: any): R;
      toContainEqual(expected: any): R;
      toHaveLength(expected: number): R;
      toMatch(expected: string | RegExp): R;
      toMatchObject(expected: object): R;
      toMatchSnapshot(hint?: string): R;
      
      // Truthiness matchers
      toBeTruthy(): R;
      toBeFalsy(): R;
      toBeNull(): R;
      toBeUndefined(): R;
      toBeDefined(): R;
      toBeNaN(): R;
      
      // Number matchers
      toBeGreaterThan(expected: number): R;
      toBeGreaterThanOrEqual(expected: number): R;
      toBeLessThan(expected: number): R;
      toBeLessThanOrEqual(expected: number): R;
      
      // Mock function matchers
      toHaveBeenCalled(): R;
      toHaveBeenCalledWith(...args: any[]): R;
      toHaveBeenCalledTimes(expected: number): R;
      toHaveBeenLastCalledWith(...args: any[]): R;
      toHaveBeenNthCalledWith(nthCall: number, ...args: any[]): R;
      toHaveReturned(): R;
      toHaveReturnedWith(expected: any): R;
      toHaveReturnedTimes(expected: number): R;
      toHaveLastReturnedWith(expected: any): R;
      toHaveNthReturnedWith(nthCall: number, expected: any): R;
      
      // Exception matchers
      toThrow(expected?: any): R;
      toThrowError(expected?: any): R;
      toThrowErrorMatchingSnapshot(hint?: string): R;
      
      // Promise matchers
      resolves: Matchers<Promise<R>>;
      rejects: Matchers<Promise<R>>;
    }
  }
}

export {};