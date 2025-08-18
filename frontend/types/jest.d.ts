/**
 * Jest Type Definitions for Test Files
 * Extends Jest's global interfaces with all custom matchers
 */

/// <reference types="jest" />
/// <reference types="@testing-library/jest-dom" />

// Augment Jest's expect interface with all available matchers
declare global {
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
    
    interface Expect {
      // Utility functions
      anything(): any;
      any(constructor: any): any;
      arrayContaining<E = any>(array: E[]): any;
      objectContaining(object: object): any;
      stringContaining(string: string): any;
      stringMatching(string: string | RegExp): any;
      
      // Assertions
      assertions(count: number): void;
      hasAssertions(): void;
    }
  }
}

export {};