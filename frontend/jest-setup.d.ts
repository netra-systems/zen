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
}

export {};