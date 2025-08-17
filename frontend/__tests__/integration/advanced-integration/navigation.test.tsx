/**
 * Navigation Flow Integration Tests
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';
import { useAuthStore } from '@/store/authStore';

describe('Advanced Frontend Integration Tests - Navigation', () => {
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    safeWebSocketCleanup();
  });

  describe('20. Complex Navigation Flows', () => {
    it('should handle deep linking with state preservation', async () => {
      const router = require('next/navigation').useRouter();
      
      const NavigationComponent = () => {
        const [navigationStack, setNavigationStack] = React.useState<string[]>(['/']);
        
        const navigateTo = (path: string, preserveState = true) => {
          if (preserveState) {
            sessionStorage.setItem('nav_state', JSON.stringify({
              from: navigationStack[navigationStack.length - 1],
              timestamp: Date.now()
            }));
          }
          
          setNavigationStack(prev => [...prev, path]);
          router.push(path);
        };
        
        const goBack = () => {
          if (navigationStack.length > 1) {
            const newStack = [...navigationStack];
            newStack.pop();
            setNavigationStack(newStack);
            router.back();
          }
        };
        
        return (
          <div>
            <div data-testid="current-path">
              {navigationStack[navigationStack.length - 1]}
            </div>
            <div data-testid="stack-depth">{navigationStack.length}</div>
            <button onClick={() => navigateTo('/chat/thread-1')}>Go to Thread</button>
            <button onClick={goBack}>Back</button>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<NavigationComponent />);
      
      expect(getByTestId('current-path')).toHaveTextContent('/');
      
      fireEvent.click(getByText('Go to Thread'));
      
      await waitFor(() => {
        expect(getByTestId('current-path')).toHaveTextContent('/chat/thread-1');
        expect(getByTestId('stack-depth')).toHaveTextContent('2');
      });
      
      // Verify state was preserved
      const savedState = JSON.parse(sessionStorage.getItem('nav_state') || '{}');
      expect(savedState.from).toBe('/');
    });

    it('should handle protected route redirects', async () => {
      const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
        const router = require('next/navigation').useRouter();
        
        React.useEffect(() => {
          if (!isAuthenticated) {
            // Save intended destination
            sessionStorage.setItem('redirect_after_login', window.location.pathname);
            router.push('/auth/login');
          }
        }, [isAuthenticated, router]);
        
        if (!isAuthenticated) {
          return <div>Redirecting to login...</div>;
        }
        
        return <>{children}</>;
      };
      
      const TestComponent = () => {
        return (
          <ProtectedRoute>
            <div data-testid="protected-content">Protected Content</div>
          </ProtectedRoute>
        );
      };
      
      // Test unauthenticated access
      const { getByText, rerender } = render(<TestComponent />);
      
      expect(getByText('Redirecting to login...')).toBeInTheDocument();
      expect(sessionStorage.getItem('redirect_after_login')).toBe('/');
      
      // Authenticate and rerender
      act(() => {
        useAuthStore.setState({ isAuthenticated: true, user: { id: '1', email: 'test@example.com' } });
      });
      
      rerender(<TestComponent />);
      
      await waitFor(() => {
        expect(screen.getByTestId('protected-content')).toBeInTheDocument();
      });
    });
  });
});