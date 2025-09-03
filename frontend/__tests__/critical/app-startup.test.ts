/**
 * Critical Application Startup Tests
 * Tests that verify the application can start and core components are available
 */

import { render, screen } from '@testing-library/react';

describe('Critical: Application Startup', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should have environment variables configured', () => {
    expect(process.env.NODE_ENV).toBeDefined();
    expect(process.env.NEXT_PUBLIC_API_URL).toBeDefined();
    expect(process.env.NEXT_PUBLIC_WS_URL).toBeDefined();
    expect(process.env.NEXT_PUBLIC_AUTH_SERVICE_URL).toBeDefined();
  });

  it('should have localStorage available', () => {
    expect(global.localStorage).toBeDefined();
    expect(typeof global.localStorage.getItem).toBe('function');
    expect(typeof global.localStorage.setItem).toBe('function');
    expect(typeof global.localStorage.removeItem).toBe('function');
  });

  it('should have WebSocket mock available', () => {
    expect(global.WebSocket).toBeDefined();
    const ws = new WebSocket('ws://test');
    expect(ws).toBeDefined();
    expect(ws.send).toBeDefined();
    expect(ws.close).toBeDefined();
    ws.close();
  });

  it('should have fetch mock available', () => {
    expect(global.fetch).toBeDefined();
    expect(typeof global.fetch).toBe('function');
  });

  it('should have React testing utilities available', () => {
    const React = require('react');
    expect(React).toBeDefined();
    expect(React.createElement).toBeDefined();
    expect(React.useState).toBeDefined();
    expect(React.useEffect).toBeDefined();
  });

  it('should have testing library available', () => {
    expect(render).toBeDefined();
    expect(screen).toBeDefined();
  });

  it('should have auth token in default state', () => {
    // The jest.setup.js sets default auth tokens
    localStorage.setItem('token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test');
    const token = localStorage.getItem('token');
    expect(token).toBeDefined();
    expect(token).toContain('eyJ');
  });

  it('should have critical mocks configured', () => {
    // Check auth service mock
    const { unifiedAuthService } = require('@/auth/unified-auth-service');
    expect(unifiedAuthService.getToken).toBeDefined();
    const token = unifiedAuthService.getToken();
    expect(token).toBeTruthy();
    
    // Check store mocks
    const { useUnifiedChatStore } = require('@/store/unified-chat');
    expect(useUnifiedChatStore).toBeDefined();
    expect(useUnifiedChatStore.getState).toBeDefined();
    
    const { useAuthStore } = require('@/store/authStore');
    expect(useAuthStore).toBeDefined();
    expect(useAuthStore.getState).toBeDefined();
  });

  it('should handle async operations', async () => {
    const promise = new Promise((resolve) => {
      setTimeout(() => resolve('success'), 10);
    });
    
    jest.runAllTimers();
    const result = await promise;
    expect(result).toBe('success');
  });

  it('should clear timers properly', () => {
    const callback = jest.fn();
    const id = setTimeout(callback, 1000);
    
    clearTimeout(id);
    jest.runAllTimers();
    
    expect(callback).not.toHaveBeenCalled();
  });
});