import React from 'react';
import { render, screen } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import ChatPage from '@/app/chat/page';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
 under 300 lines
 * @compliance type_safety.xml - Strongly typed test with clear interfaces
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { useRouter, useSearchParams } from 'next/navigation';
import ChatPage from '@/app/chat/page';

// Mock dependencies
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn()
}));

jest.mock('@/components/chat/MainChat', () => {
  return function MockMainChat() {
    return <div data-testid="main-chat">MainChat Component</div>;
  };
});

describe('ChatPage Component', () => {
    jest.setTimeout(10000);
  const mockPush = jest.fn();
  const mockReplace = jest.fn();
  const mockGet = jest.fn();
  const mockSearchParams = {
    get: mockGet
  };
  
  // Mock localStorage
  const mockLocalStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  };
  
  // Mock window.history
  const mockHistory = {
    replaceState: jest.fn()
  };
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock console.log to suppress output during tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
    
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      replace: mockReplace
    });
    
    (useSearchParams as jest.Mock).mockReturnValue(mockSearchParams);
    
    // Setup localStorage mock with proper getItem behavior
    mockLocalStorage.getItem.mockImplementation((key: string) => {
      // Simulate localStorage returning the value that was just set
      if (key === 'jwt_token') return 'test-jwt-token';
      if (key === 'refresh_token') return 'test-refresh-token';
      return null;
    });
    
    // Setup localStorage mock
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true
    });
    
    // Setup history mock
    Object.defineProperty(window, 'history', {
      value: mockHistory,
      writable: true
    });
    
    // Reset mocks
    mockGet.mockReturnValue(null);
  });
  
  afterEach(() => {
    // Restore console.log
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });
  
  /**
   * Test 1: Renders MainChat component
   */
  it('should render MainChat component', () => {
    render(<ChatPage />);
    
    const mainChat = screen.getByTestId('main-chat');
    expect(mainChat).toBeInTheDocument();
    expect(mainChat).toHaveTextContent('MainChat Component');
  });
  
  /**
   * Test 2: Handles OAuth tokens from URL parameters
   */
  it('should handle OAuth tokens from URL parameters', () => {
    mockGet.mockImplementation((key: string) => {
      if (key === 'token') return 'test-jwt-token';
      if (key === 'refresh') return 'test-refresh-token';
      return null;
    });
    
    render(<ChatPage />);
    
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', 'test-jwt-token');
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('refresh_token', 'test-refresh-token');
    expect(mockHistory.replaceState).toHaveBeenCalledWith({}, '', '/chat');
  });
  
  /**
   * Test 3: Handles OAuth token without refresh token
   */
  it('should handle OAuth token without refresh token', () => {
    mockGet.mockImplementation((key: string) => {
      if (key === 'token') return 'test-jwt-token';
      return null;
    });
    
    render(<ChatPage />);
    
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', 'test-jwt-token');
    expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith('refresh_token', expect.anything());
    expect(mockHistory.replaceState).toHaveBeenCalledWith({}, '', '/chat');
  });
  
  /**
   * Test 4: Does not process tokens when none present
   */
  it('should not process tokens when none are present in URL', () => {
    render(<ChatPage />);
    
    expect(mockLocalStorage.setItem).not.toHaveBeenCalled();
    expect(mockHistory.replaceState).not.toHaveBeenCalled();
  });
  
  /**
   * Test 5: Handles thread parameter redirect
   */
  it('should redirect to thread when thread parameter is present', () => {
    mockGet.mockImplementation((key: string) => {
      if (key === 'thread') return 'thread-123';
      return null;
    });
    
    render(<ChatPage />);
    
    expect(mockReplace).toHaveBeenCalledWith('/chat/thread-123');
  });
  
  /**
   * Test 6: Does not redirect when both token and thread are present
   */
  it('should not redirect to thread when both token and thread parameters are present', () => {
    mockGet.mockImplementation((key: string) => {
      if (key === 'token') return 'test-jwt-token';
      if (key === 'thread') return 'thread-123';
      return null;
    });
    
    render(<ChatPage />);
    
    expect(mockReplace).not.toHaveBeenCalled();
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('jwt_token', 'test-jwt-token');
  });
  
  /**
   * Test 7: Does not redirect when no thread parameter
   */
  it('should not redirect when no thread parameter is present', () => {
    render(<ChatPage />);
    
    expect(mockReplace).not.toHaveBeenCalled();
  });
});