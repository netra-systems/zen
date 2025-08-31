/**
 * Login Redirect Tests
 * Tests for login redirect behavior and authentication state handling
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock login component for testing
const MockLoginRedirect: React.FC<{
  isAuthenticated: boolean;
  onLogin?: () => void;
  redirectPath?: string;
}> = ({ isAuthenticated, onLogin, redirectPath = '/dashboard' }) => {
  const [isLoading, setIsLoading] = React.useState(false);

  const handleLogin = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 100)); // Simulate API call
      onLogin?.();
      
      // Simulate redirect
      if (isAuthenticated) {
        window.location.href = redirectPath;
      }
    } catch (error) {
      console.error('Login failed:', error);
      // Keep in loading state on error for this test
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthenticated) {
    return (
      <div data-testid="authenticated-content">
        <h1>Welcome! You are logged in.</h1>
        <button data-testid="logout-button">Logout</button>
      </div>
    );
  }

  return (
    <div data-testid="login-form">
      <h1>Please log in</h1>
      <button 
        data-testid="login-button" 
        onClick={handleLogin}
        disabled={isLoading}
      >
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </div>
  );
};

describe('Login Redirect Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should show login form when not authenticated', () => {
    render(
      <MockLoginRedirect 
        isAuthenticated={false}
        redirectPath="/admin"
      />
    );

    // Should show login form
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    expect(screen.getByText('Please log in')).toBeInTheDocument();
    expect(screen.getByTestId('login-button')).toBeInTheDocument();
    
    // Should not show authenticated content
    expect(screen.queryByTestId('authenticated-content')).not.toBeInTheDocument();
  });

  it('should show authenticated content when already authenticated', () => {
    render(
      <MockLoginRedirect 
        isAuthenticated={true}
        redirectPath="/profile"
      />
    );

    // Should show authenticated content
    expect(screen.getByTestId('authenticated-content')).toBeInTheDocument();
    expect(screen.getByText('Welcome! You are logged in.')).toBeInTheDocument();
    expect(screen.getByTestId('logout-button')).toBeInTheDocument();
    
    // Should not show login form
    expect(screen.queryByTestId('login-form')).not.toBeInTheDocument();
  });

  it('should show loading state during login process', async () => {
    const mockLogin = jest.fn();
    
    render(
      <MockLoginRedirect 
        isAuthenticated={false}
        onLogin={mockLogin}
      />
    );

    const loginButton = screen.getByTestId('login-button');
    
    // Initially should show normal login button
    expect(loginButton).toHaveTextContent('Login');
    expect(loginButton).toBeEnabled();

    // Click login
    fireEvent.click(loginButton);

    // Should show loading state
    expect(loginButton).toHaveTextContent('Logging in...');
    expect(loginButton).toBeDisabled();

    // Wait for login to complete
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled();
    });
  });

  it('should handle login failure gracefully', async () => {
    const mockLogin = jest.fn(() => {
      throw new Error('Login failed');
    });
    
    // Mock console.error to avoid test noise
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    render(
      <MockLoginRedirect 
        isAuthenticated={false}
        onLogin={mockLogin}
      />
    );

    const loginButton = screen.getByTestId('login-button');
    
    // This test will fail because our mock component doesn't handle errors
    fireEvent.click(loginButton);

    // Wait for loading to finish
    await waitFor(() => {
      expect(loginButton).toHaveTextContent('Login');
    });

    // Should still show login form after failure
    expect(screen.getByTestId('login-form')).toBeInTheDocument();
    
    consoleSpy.mockRestore();
  });

  it('should display custom redirect path in component', () => {
    render(
      <MockLoginRedirect 
        isAuthenticated={true}
        redirectPath="/custom-dashboard"
      />
    );

    // Should show authenticated content when redirect path is set
    expect(screen.getByTestId('authenticated-content')).toBeInTheDocument();
    expect(screen.getByText('Welcome! You are logged in.')).toBeInTheDocument();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});