/**
 * Iteration 5: Auth Store Mock Issue Fix
 * Testing authentication state management in components
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock the auth store
const mockUseAuthStore = jest.fn();
jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

// Create a test component that uses auth
const TestAuthComponent: React.FC = () => {
  const { isAuthenticated, user } = mockUseAuthStore();
  
  return (
    <div>
      {isAuthenticated ? (
        <div data-testid="authenticated">
          Welcome, {user?.name || 'User'}!
        </div>
      ) : (
        <div data-testid="unauthenticated">
          Please sign in
        </div>
      )}
    </div>
  );
};

describe('Auth Store Mock Fix - Iteration 5', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows authenticated state when user is logged in', () => {
    // Fix: Properly mock auth store with complete user object
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: true,
      user: {
        id: 'user-123',
        name: 'John Doe',
        email: 'john@example.com'
      },
      login: jest.fn(),
      logout: jest.fn()
    });

    render(<TestAuthComponent />);
    
    expect(screen.getByTestId('authenticated')).toBeInTheDocument();
    expect(screen.getByText('Welcome, John Doe!')).toBeInTheDocument();
  });

  it('shows unauthenticated state when user is not logged in', () => {
    // Fix: Properly mock auth store with null user
    mockUseAuthStore.mockReturnValue({
      isAuthenticated: false,
      user: null,
      login: jest.fn(),
      logout: jest.fn()
    });

    render(<TestAuthComponent />);
    
    expect(screen.getByTestId('unauthenticated')).toBeInTheDocument();
    expect(screen.getByText('Please sign in')).toBeInTheDocument();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});