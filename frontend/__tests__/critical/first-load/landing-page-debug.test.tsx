/**
 * Debug Test - Figure out why the auth mock isn't working
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { jest } from '@jest/globals';

// Mock router first
const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
    prefetch: jest.fn(),
  }),
}));

// Mock the auth service to return controlled states
const mockUseAuth = jest.fn();

// Try to override the jest.setup.js mock completely
jest.mock('@/auth', () => ({
  authService: {
    useAuth: mockUseAuth,
  },
}));

// Import after mocks are set up
import HomePage from '@/app/page';

describe('Debug Landing Page Auth', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPush.mockClear();
    mockReplace.mockClear();
    mockUseAuth.mockClear();
    
    // Add spy to the actual authService import to see what's being called
    console.log('Clearing mocks...');
  });

  it('should debug what auth function is actually being called', async () => {
    // Setup a mock that logs when called
    mockUseAuth.mockImplementation(() => {
      console.log('mockUseAuth WAS CALLED!');
      return {
        user: null,
        loading: false,
        error: null,
      };
    });

    console.log('Before render');
    
    render(<HomePage />);
    
    console.log('After render');
    console.log('mockUseAuth call count:', mockUseAuth.mock.calls.length);
    console.log('mockPush call count:', mockPush.mock.calls.length);
    
    // Let's also check what the actual DOM looks like
    screen.debug();
  });

  it('should test if the component can be imported at all', () => {
    console.log('HomePage component type:', typeof HomePage);
    console.log('HomePage component:', HomePage);
    expect(HomePage).toBeDefined();
    expect(typeof HomePage).toBe('function');
  });

  it('should test direct mock functionality', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
      error: null,
    });
    
    const result = mockUseAuth();
    console.log('Direct mock call result:', result);
    expect(result.loading).toBe(false);
    expect(result.user).toBeNull();
  });
});