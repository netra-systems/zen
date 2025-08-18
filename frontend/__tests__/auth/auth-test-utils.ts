/**
 * Shared Auth Testing Utilities
 * =============================
 * Centralized mocks, setup, and utilities for auth test modules
 * 
 * BVJ: Enterprise segment - ensures security compliance, prevents auth vulnerabilities
 * Modular design: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { AuthContext } from '@/auth';

// Mock dependencies
jest.mock('@/config', () => ({
  config: {
    apiUrl: 'http://localhost:8081'
  }
}));

// Mock React.useContext
export const mockUseContext = jest.fn();
jest.mock('react', () => ({
  ...jest.requireActual('react'),
  useContext: jest.fn()
}));
// @ts-ignore
React.useContext = mockUseContext;

// Mock localStorage utilities
export const createLocalStorageMock = () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
});

export const setupLocalStorageMock = () => {
  const localStorageMock = createLocalStorageMock();
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock
  });
  return localStorageMock;
};

// Location mock utilities
export const createLocationMock = () => {
  let mockHref = 'http://localhost/';
  
  const mockLocationAssign = jest.fn();
  const mockLocationReplace = jest.fn();
  const mockLocationReload = jest.fn();

  const locationMock: any = {
    assign: mockLocationAssign,
    replace: mockLocationReplace,
    reload: mockLocationReload,
    origin: 'http://localhost:3000',
    pathname: '/',
    search: '',
    hash: '',
    toString: () => mockHref
  };

  Object.defineProperty(locationMock, 'href', {
    get: () => mockHref,
    set: (value: string) => {
      mockHref = value;
    },
    configurable: true,
    enumerable: true
  });

  return {
    locationMock,
    mockLocationAssign,
    mockLocationReplace,
    mockLocationReload,
    getMockHref: () => mockHref,
    setMockHref: (href: string) => { mockHref = href; }
  };
};

export const setupWindowLocation = () => {
  delete (window as any)['location'];
  const locationUtils = createLocationMock();
  window.location = locationUtils.locationMock;
  return locationUtils;
};

// Mock fetch setup
export const setupFetchMock = () => {
  global.fetch = jest.fn();
  return global.fetch as jest.Mock;
};

// Test data factories
export const createMockAuthConfig = () => ({
  google_client_id: 'test-client-id',
  development_mode: false,
  endpoints: {
    login: 'http://localhost:8081/auth/login',
    logout: 'http://localhost:8081/auth/logout',
    callback: 'http://localhost:8081/auth/callback',
    token: 'http://localhost:8081/auth/token',
    user: 'http://localhost:8081/auth/me',
    dev_login: 'http://localhost:8081/auth/dev-login'
  },
  authorized_javascript_origins: ['http://localhost:3000'],
  authorized_redirect_uris: ['http://localhost:3000/callback']
});

export const createMockDevConfig = () => ({
  ...createMockAuthConfig(),
  development_mode: true
});

export const createMockToken = () => 'mock-jwt-token-123';

export const createMockDevLoginResponse = () => ({
  access_token: createMockToken(),
  token_type: 'Bearer'
});

export const createMockAuthContext = () => ({
  user: null,
  login: jest.fn(),
  logout: jest.fn(),
  loading: false,
  authConfig: null,
  token: null
});

// Test setup helpers
export const setupAuthTestEnvironment = () => {
  const localStorageMock = setupLocalStorageMock();
  const locationUtils = setupWindowLocation();
  const fetchMock = setupFetchMock();
  
  return {
    localStorageMock,
    locationUtils,
    fetchMock
  };
};

export const resetAuthTestMocks = (mocks: ReturnType<typeof setupAuthTestEnvironment>) => {
  jest.clearAllMocks();
  mocks.locationUtils.setMockHref('http://localhost/');
  mocks.localStorageMock.getItem.mockReturnValue(null);
};

// Response builders
export const createSuccessResponse = (data: any) => ({
  ok: true,
  json: jest.fn().mockResolvedValue(data)
});

export const createErrorResponse = (status: number, statusText?: string) => ({
  ok: false,
  status,
  statusText: statusText || 'Error'
});

export const createNetworkError = (message: string = 'Network error') => {
  return new Error(message);
};

// Mock console utilities
export const mockConsoleMethod = (method: 'info' | 'error' | 'warn' | 'log') => {
  return jest.spyOn(console, method).mockImplementation();
};

export const restoreConsoleMock = (spy: jest.SpyInstance) => {
  spy.mockRestore();
};

// Assertion helpers
export const expectFetchCall = (
  fetchMock: jest.Mock,
  url: string,
  options?: any
) => {
  expect(fetchMock).toHaveBeenCalledWith(url, options);
};

export const expectLocalStorageSet = (
  localStorageMock: any,
  key: string,
  value: string
) => {
  expect(localStorageMock.setItem).toHaveBeenCalledWith(key, value);
};

export const expectLocalStorageRemove = (
  localStorageMock: any,
  key: string
) => {
  expect(localStorageMock.removeItem).toHaveBeenCalledWith(key);
};

export const expectAuthHeaders = (headers: any, token: string) => {
  expect(headers).toEqual({ Authorization: `Bearer ${token}` });
};

export const expectEmptyHeaders = (headers: any) => {
  expect(headers).toEqual({});
};

// Test validation helpers
export const validateTokenOperation = (
  localStorageMock: any,
  operation: 'get' | 'set' | 'remove',
  key: string = 'jwt_token',
  value?: string
) => {
  switch (operation) {
    case 'get':
      expect(localStorageMock.getItem).toHaveBeenCalledWith(key);
      break;
    case 'set':
      expect(localStorageMock.setItem).toHaveBeenCalledWith(key, value);
      break;
    case 'remove':
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(key);
      break;
  }
};

export const validateDevLoginCall = (
  fetchMock: jest.Mock,
  authConfig: any
) => {
  const expectedBody = JSON.stringify({ email: 'dev@example.com' });
  const expectedOptions = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: expectedBody
  };
  
  expectFetchCall(fetchMock, authConfig.endpoints.dev_login, expectedOptions);
};

export const validateLogoutCall = (
  fetchMock: jest.Mock,
  authConfig: any,
  token?: string
) => {
  const headers: any = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  
  const expectedOptions = {
    method: 'POST',
    headers
  };
  
  expectFetchCall(fetchMock, authConfig.endpoints.logout, expectedOptions);
};

// Security test helpers
export const validateSecureTokenStorage = (
  localStorageMock: any,
  token: string
) => {
  expectLocalStorageSet(localStorageMock, 'jwt_token', token);
  expectLocalStorageRemove(localStorageMock, 'dev_logout_flag');
};

export const validateSecureLogout = (localStorageMock: any) => {
  expectLocalStorageRemove(localStorageMock, 'jwt_token');
};

export const validateSecureHeaders = (headers: any) => {
  const headerKeys = Object.keys(headers);
  expect(headerKeys).toEqual(['Authorization']);
  expect(headers.Authorization).toMatch(/^Bearer /);
};