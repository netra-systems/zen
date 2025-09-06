import React from 'react';
import { render } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { AuthGuard } from '@/components/AuthGuard';
import { AuthContext, AuthContextType } from '@/auth/context';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock GTM hooks
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: () => ({
    trackError: jest.fn(),
    trackPageView: jest.fn(),
  }),
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
  }
}));

describe('Debug Auth Test', () => {
  it('should debug localStorage behavior', () => {
    console.log('=== localStorage debug ===');
    console.log('Initial localStorage state:');
    console.log('jwt_token:', localStorage.getItem('jwt_token'));
    console.log('token:', localStorage.getItem('token'));
    
    // Clear localStorage
    localStorage.clear();
    console.log('After localStorage.clear():');
    console.log('jwt_token:', localStorage.getItem('jwt_token'));
    console.log('token:', localStorage.getItem('token'));
    
    // Check if the afterEach hook restoration happens
    setTimeout(() => {
      console.log('After timeout:');
      console.log('jwt_token:', localStorage.getItem('jwt_token'));
      console.log('token:', localStorage.getItem('token'));
    }, 100);
  });
  
  it('should debug AuthGuard with no token', async () => {
    const mockPush = jest.fn();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
      pathname: '/protected',
    });
    
    // Mock window.location
    delete (window as any).location;
    (window as any).location = { pathname: '/protected' };
    
    // Clear localStorage completely
    localStorage.clear();
    console.log('Test: jwt_token after clear:', localStorage.getItem('jwt_token'));
    
    const authValue: AuthContextType = {
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      authConfig: null,
      token: null,
      initialized: true,
    };
    
    render(
      <AuthContext.Provider value={authValue}>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </AuthContext.Provider>
    );
    
    // Wait for useEffect
    await new Promise(resolve => setTimeout(resolve, 50));
    
    console.log('mockPush calls:', mockPush.mock.calls);
    console.log('mockPush call count:', mockPush.mock.calls.length);
  });
});