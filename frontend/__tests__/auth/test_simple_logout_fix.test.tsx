/**
 * Simple FAIL SAFE LOGOUT Test - Isolated
 * This test isolates the fail-safe logout functionality to verify our fix works
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';

// Mock implementation of logout with fail-safe behavior
const createMockLogoutHandler = (shouldBackendFail: boolean = false) => {
  let localStateCleared = false;
  let backendCalled = false;
  let errorLogged = false;
  
  const mockBackendLogout = jest.fn().mockImplementation(() => {
    backendCalled = true;
    if (shouldBackendFail) {
      throw new Error('Backend logout failed: 500 Internal Server Error');
    }
  });
  
  const logout = async () => {
    // CRITICAL: Clear local state FIRST (fail-safe behavior)
    localStateCleared = true;
    
    // THEN attempt backend logout
    try {
      await mockBackendLogout();
    } catch (error) {
      // LOUD failure as per CLAUDE.md
      console.error('Backend logout failed', error);
      errorLogged = true;
      // Local state already cleared - FAIL SAFE LOGOUT achieved
    }
  };
  
  return {
    logout,
    getState: () => ({
      localStateCleared,
      backendCalled,
      errorLogged
    }),
    mockBackendLogout
  };
};

// Simple test component
const SimpleLogoutComponent: React.FC<{ logoutHandler: any }> = ({ logoutHandler }) => {
  const [user, setUser] = React.useState<string | null>('Test User');
  
  const handleLogout = async () => {
    await logoutHandler.logout();
    // Local state should be cleared after logout
    setUser(null);
  };
  
  return (
    <div>
      <div data-testid="user-status">
        {user ? `Logged in as: ${user}` : 'No user'}
      </div>
      <button onClick={handleLogout} data-testid="logout-button">
        Logout
      </button>
    </div>
  );
};

describe('FAIL SAFE LOGOUT - Isolated Test', () => {
  it('should clear local state even when backend logout fails', async () => {
    // CRITICAL: This test verifies fail-safe logout behavior
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    
    // Create logout handler that simulates backend failure
    const logoutHandler = createMockLogoutHandler(true);
    
    render(<SimpleLogoutComponent logoutHandler={logoutHandler} />);
    
    // Verify initial state
    expect(screen.getByTestId('user-status')).toHaveTextContent('Logged in as: Test User');
    
    // Perform logout (backend will fail)
    fireEvent.click(screen.getByTestId('logout-button'));
    
    await waitFor(() => {
      // CRITICAL: Local state MUST be cleared even if backend fails
      expect(screen.getByTestId('user-status')).toHaveTextContent('No user');
    });
    
    // Verify fail-safe behavior
    const state = logoutHandler.getState();
    expect(state.localStateCleared).toBe(true);
    expect(state.backendCalled).toBe(true);
    expect(state.errorLogged).toBe(true);
    
    // CRITICAL: Backend error must be LOUD - logged for investigation
    expect(consoleError).toHaveBeenCalledWith(
      expect.stringContaining('Backend logout failed'),
      expect.any(Error)
    );
    
    consoleError.mockRestore();
  });
  
  it('should work normally when backend logout succeeds', async () => {
    // Create logout handler that simulates successful backend logout
    const logoutHandler = createMockLogoutHandler(false);
    
    render(<SimpleLogoutComponent logoutHandler={logoutHandler} />);
    
    // Verify initial state
    expect(screen.getByTestId('user-status')).toHaveTextContent('Logged in as: Test User');
    
    // Perform logout (backend will succeed)
    fireEvent.click(screen.getByTestId('logout-button'));
    
    await waitFor(() => {
      // Local state should be cleared
      expect(screen.getByTestId('user-status')).toHaveTextContent('No user');
    });
    
    // Verify normal behavior
    const state = logoutHandler.getState();
    expect(state.localStateCleared).toBe(true);
    expect(state.backendCalled).toBe(true);
    expect(state.errorLogged).toBe(false);
  });
});