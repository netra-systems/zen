/**
 * Shared test setup and utilities for advanced integration tests
 */

import React from 'react';
import '@testing-library/jest-dom';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

// Mock Next.js
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

export const setupTestEnvironment = () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    process.env.NEXT_PUBLIC_WS_URL = 'ws://localhost:8000';
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    // Reset stores
    useAuthStore.setState({ user: null, token: null, isAuthenticated: false });
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], activeThread: null });
    
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });
};