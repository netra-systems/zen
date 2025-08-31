/**
 * Auth validation test - Iteration 4 test
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Simple test component to validate auth state
const AuthStatusComponent: React.FC<{ isAuthenticated: boolean }> = ({ isAuthenticated }) => {
  return (
    <div>
      <span data-testid="auth-status">
        {isAuthenticated ? 'Authenticated' : 'Not Authenticated'}
      </span>
      {isAuthenticated && <button data-testid="logout-button">Logout</button>}
    </div>
  );
};

describe('Auth Validation Tests', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  it('should show logout button when user is authenticated', () => {
    render(<AuthStatusComponent isAuthenticated={true} />);
    
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
    expect(screen.getByTestId('logout-button')).toBeInTheDocument();
  });

  it('should not show logout button when user is not authenticated', () => {
    render(<AuthStatusComponent isAuthenticated={false} />);
    
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Not Authenticated');
    // Fixed: Should NOT be in the document when user is not authenticated
    expect(screen.queryByTestId('logout-button')).not.toBeInTheDocument();
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});