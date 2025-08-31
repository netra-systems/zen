import React from 'react';
import { render as renderWithProviders, screen, fireEvent, waitFor, act, withRouter } from '../utils/test-utils';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
// Using Jest, not vitest
import { ErrorFallback } from '@/components/ErrorFallback';
import { Header } from '@/components/Header';
import { NavLinks } from '@/components/NavLinks';

// Mock authService
jest.mock('@/auth', () => ({
  authService: {
    useAuth: jest.fn(() => ({
      user: {
        id: 'test-user',
        email: 'test@example.com',
        name: 'Test User'
      },
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null,
      token: 'mock-token'
    }))
  }
}));

// Test 62: ErrorFallback recovery
describe('test_ErrorFallback_recovery', () => {
    jest.setTimeout(10000);
  it('should display error boundary correctly', () => {
    const error = new Error('Test error');
    const resetErrorBoundary = jest.fn();
    
    // Set NODE_ENV to development to show error details
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Test error/i)).toHaveLength(2); // One in error message, one in stack trace
    expect(screen.getByRole('button', { name: /Try again/i })).toBeInTheDocument();
    
    // Restore original environment
    process.env.NODE_ENV = originalEnv;
  });

  it('should handle recovery actions', () => {
    const error = new Error('Test error');
    const resetErrorBoundary = jest.fn();
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    const retryButton = screen.getByRole('button', { name: /Try again/i });
    fireEvent.click(retryButton);
    
    expect(resetErrorBoundary).toHaveBeenCalledTimes(1);
  });

  it('should display stack trace in development mode', () => {
    const error = new Error('Test error');
    error.stack = 'Error: Test error\n    at TestComponent (test.js:10:5)';
    const resetErrorBoundary = jest.fn();
    
    // Mock development environment
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    expect(screen.getByText(/test.js:10:5/i)).toBeInTheDocument();
    
    process.env.NODE_ENV = originalEnv;
  });
});

// Test 63: Header navigation
describe('test_Header_navigation', () => {
    jest.setTimeout(10000);
  it('should render header components correctly', () => {
    const mockToggleSidebar = jest.fn();
    renderWithProviders(withRouter(<Header toggleSidebar={mockToggleSidebar} />));
    
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByText(/Toggle navigation menu/i)).toBeInTheDocument();
  });

  it('should handle navigation interactions', async () => {
    const mockToggleSidebar = jest.fn();
    renderWithProviders(
withRouter(<Header toggleSidebar={mockToggleSidebar} />)
    );
    
    const toggleButton = screen.getByRole('button', { name: /Toggle navigation menu/i });
    fireEvent.click(toggleButton);
    
    expect(mockToggleSidebar).toHaveBeenCalledTimes(1);
  });

  it('should show responsive menu on mobile', () => {
    // Mock mobile viewport
    window.innerWidth = 375;
    window.dispatchEvent(new Event('resize'));
    
    const mockToggleSidebar = jest.fn();
    renderWithProviders(
withRouter(<Header toggleSidebar={mockToggleSidebar} />)
    );
    
    const menuButton = screen.getByRole('button', { name: /Toggle navigation menu/i });
    expect(menuButton).toBeInTheDocument();
    
    fireEvent.click(menuButton);
    expect(mockToggleSidebar).toHaveBeenCalledTimes(1);
  });
});

// Test 64: NavLinks routing  
describe('test_NavLinks_routing', () => {
    jest.setTimeout(10000);
  it('should render navigation links correctly when user is authenticated', () => {
    renderWithProviders(
withRouter(<NavLinks />)
    );
    
    // Note: Actual navigation items are Chat based on the component
    expect(screen.getByRole('link', { name: /Chat/i })).toBeInTheDocument();
  });

  it('should render login link when user is not authenticated', () => {
    // Mock authService to return no user
    const { authService } = require('@/auth');
    authService.useAuth.mockReturnValue({
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null,
      token: null
    });
    
    renderWithProviders(
withRouter(<NavLinks />)
    );
    
    // When no user is authenticated, it should show a login link
    expect(screen.getByRole('link', { name: /Login/i })).toBeInTheDocument();
  });

  it('should handle navigation correctly', () => {
    // Reset the auth mock to ensure authenticated state
    const { authService } = require('@/auth');
    authService.useAuth.mockReturnValue({
      user: {
        id: 'test-user',
        email: 'test@example.com',
        name: 'Test User'
      },
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null,
      token: 'mock-token'
    });

    renderWithProviders(
withRouter(<NavLinks />)
    );
    
    // Since the user is authenticated (from our mock), there should be a Chat link
    const chatLinks = screen.getAllByRole('link', { name: /Chat/i });
    expect(chatLinks).toHaveLength(1);
    expect(chatLinks[0]).toHaveAttribute('href', '/chat');
  });
});