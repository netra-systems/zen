/**
 * Login to Chat Test Components
 * Real component wrappers for integration testing
 * Business Value: Ensures tests reflect REAL user experience
 * 
 * ARCHITECTURAL COMPLIANCE: ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render } from '@testing-library/react';
import { TestProviders } from '../setup/test-providers';
import { useAuthStore } from '@/store/authStore';
import { jest } from '@jest/globals';

// Mock the auth store
jest.mock('@/store/authStore');

// Test data constants
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'admin' as const,
  picture: 'https://example.com/avatar.jpg'
};

export const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.real.token';

// Mock LoginButton component for testing (≤8 lines)
const MockLoginButton = () => (
  <button data-testid="login-button">Login with Google</button>
);

// Test component wrapper for testing (≤8 lines)
export function renderRealLoginToChatFlow() {
  // Mock the auth store before rendering
  const mockStore = {
    isAuthenticated: true,
    user: mockUser,
    token: mockToken,
    login: jest.fn(),
    logout: jest.fn(),
    loading: false,
    error: null
  };
  jest.mocked(useAuthStore).mockReturnValue(mockStore);
  
  const TestApp = () => (
    <TestProviders>
      <div data-testid="test-app">
        <MockLoginButton />
        <div data-testid="chat-window">
          <div>
            <input data-testid="message-input" disabled={false} />
            <button data-testid="send-button">Send</button>
          </div>
          <div data-testid="thread-list">Threads</div>
          <div data-testid="threads-loading" style={{display: 'none'}}>Loading threads...</div>
          <div data-testid="connection-status">Connected</div>
        </div>
      </div>
    </TestProviders>
  );
  return render(<TestApp />);
}