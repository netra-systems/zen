import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GTMProvider } from '@/providers/GTMProvider';
import { useGTM } from '@/hooks/useGTM';
import { AuthProvider } from '@/auth/context';

// Mock Next.js components
jest.mock('next/script', () => {
  return function MockScript({ onLoad, onReady, ...props }: any) {
    React.useEffect(() => {
      if (onReady) onReady();
      const timer = setTimeout(() => {
        if (onLoad) onLoad();
      }, 100);
      return () => clearTimeout(timer);
    }, [onLoad, onReady]);
    return <script {...props} data-testid="gtm-script" />;
  };
});

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    pathname: '/login',
    query: {},
  }),
  usePathname: () => '/login',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock auth service
const mockAuthService = {
  login: jest.fn(),
  logout: jest.fn(),
  signup: jest.fn(),
  getCurrentUser: jest.fn(),
  isAuthenticated: jest.fn(),
  getToken: jest.fn(),
};

jest.mock('@/auth/service', () => ({
  authService: mockAuthService,
}));

// Mock logger
jest.mock('@/lib/logger', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Test component that simulates authentication flow
const AuthFlowTestComponent: React.FC = () => {
  const gtm = useGTM();
  const [user, setUser] = React.useState<any>(null);
  const [authStatus, setAuthStatus] = React.useState<'idle' | 'logging-in' | 'logged-in' | 'logging-out'>('idle');

  const handleLogin = async (method: 'email' | 'google' = 'email') => {
    setAuthStatus('logging-in');
    
    // Simulate authentication
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const mockUser = {
      id: 'user123',
      email: 'test@example.com',
      name: 'Test User',
      tier: 'free' as const,
      isNewUser: false
    };

    setUser(mockUser);
    setAuthStatus('logged-in');

    // Track login event
    gtm.events.trackAuth('user_login', {
      auth_method: method,
      is_new_user: mockUser.isNewUser,
      user_tier: mockUser.tier,
      user_id: mockUser.id
    });
  };

  const handleSignup = async (method: 'email' | 'google' = 'email') => {
    setAuthStatus('logging-in');
    
    await new Promise(resolve => setTimeout(resolve, 150));
    
    const mockUser = {
      id: 'newuser456',
      email: 'newuser@example.com',
      name: 'New User',
      tier: 'free' as const,
      isNewUser: true
    };

    setUser(mockUser);
    setAuthStatus('logged-in');

    // Track signup event
    gtm.events.trackAuth('user_signup', {
      auth_method: method,
      is_new_user: mockUser.isNewUser,
      user_tier: mockUser.tier,
      user_id: mockUser.id
    });
  };

  const handleOAuthComplete = async () => {
    // Simulate OAuth completion
    await new Promise(resolve => setTimeout(resolve, 50));

    gtm.events.trackAuth('oauth_complete', {
      auth_method: 'oauth',
      user_id: user?.id
    });
  };

  const handleLogout = async () => {
    setAuthStatus('logging-out');
    
    const currentUserId = user?.id;
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    setUser(null);
    setAuthStatus('idle');

    // Track logout event
    gtm.events.trackAuth('user_logout', {
      user_id: currentUserId
    });
  };

  return (
    <div data-testid="auth-flow-component">
      <div data-testid="auth-status">{authStatus}</div>
      <div data-testid="user-info">{user ? JSON.stringify(user) : 'No user'}</div>
      <div data-testid="gtm-status">{gtm.isLoaded ? 'GTM Ready' : 'GTM Loading'}</div>
      <div data-testid="total-events">{gtm.debug.totalEvents}</div>
      
      <button data-testid="login-email-btn" onClick={() => handleLogin('email')}>
        Login with Email
      </button>
      <button data-testid="login-google-btn" onClick={() => handleLogin('google')}>
        Login with Google
      </button>
      <button data-testid="signup-email-btn" onClick={() => handleSignup('email')}>
        Signup with Email
      </button>
      <button data-testid="signup-google-btn" onClick={() => handleSignup('google')}>
        Signup with Google
      </button>
      <button data-testid="oauth-complete-btn" onClick={handleOAuthComplete}>
        Complete OAuth
      </button>
      <button data-testid="logout-btn" onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
};

describe('GTM Authentication Flow Integration', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  let mockDataLayer: any[];

  beforeEach(() => {
    mockDataLayer = [];
    Object.defineProperty(global, 'window', {
      value: {
        dataLayer: mockDataLayer,
        location: {
          pathname: '/login',
          origin: 'https://app.netra.com'
        }
      },
      writable: true
    });

    // Reset mocks
    jest.clearAllMocks();
  });

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <GTMProvider enabled={true} config={{ debug: true }}>
        {component}
      </GTMProvider>
    );
  };

  describe('Login Flow Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track email login events end-to-end', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      // Wait for GTM to be ready
      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Perform login
      fireEvent.click(screen.getByTestId('login-email-btn'));

      // Wait for auth flow to complete
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Verify GTM event tracking
      await waitFor(() => {
        const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(loginEvent).toBeDefined();
        expect(loginEvent.event_category).toBe('authentication');
        expect(loginEvent.auth_method).toBe('email');
        expect(loginEvent.is_new_user).toBe(false);
        expect(loginEvent.user_tier).toBe('free');
        expect(loginEvent.user_id).toBe('user123');
        expect(loginEvent.timestamp).toBeDefined();
        expect(loginEvent.page_path).toBe('/login');
      });

      // Verify event count updated
      expect(screen.getByTestId('total-events')).toHaveTextContent('1');
    });

    it('should track Google OAuth login events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Perform Google login
      fireEvent.click(screen.getByTestId('login-google-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Verify GTM event tracking
      await waitFor(() => {
        const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(loginEvent).toBeDefined();
        expect(loginEvent.auth_method).toBe('google');
        expect(loginEvent.user_id).toBe('user123');
      });
    });

    it('should handle login errors gracefully', async () => {
      // Mock login failure
      const failingComponent = () => {
        const gtm = useGTM();
        
        const handleFailedLogin = async () => {
          try {
            throw new Error('Authentication failed');
          } catch (error) {
            // Track error event
            gtm.events.trackCustom({
              event: 'auth_error',
              event_category: 'authentication',
              event_action: 'login_failed',
              error_message: (error as Error).message
            });
          }
        };

        return (
          <div>
            <button data-testid="fail-login-btn" onClick={handleFailedLogin}>
              Fail Login
            </button>
          </div>
        );
      };

      renderWithProviders(React.createElement(failingComponent));

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      fireEvent.click(screen.getByTestId('fail-login-btn'));

      await waitFor(() => {
        const errorEvent = mockDataLayer.find(item => item.event === 'auth_error');
        expect(errorEvent).toBeDefined();
        expect(errorEvent.event_action).toBe('login_failed');
        expect(errorEvent.error_message).toBe('Authentication failed');
      });
    });
  });

  describe('Signup Flow Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track new user signup events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Perform signup
      fireEvent.click(screen.getByTestId('signup-email-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Verify signup event
      await waitFor(() => {
        const signupEvent = mockDataLayer.find(item => item.event === 'user_signup');
        expect(signupEvent).toBeDefined();
        expect(signupEvent.event_category).toBe('authentication');
        expect(signupEvent.auth_method).toBe('email');
        expect(signupEvent.is_new_user).toBe(true);
        expect(signupEvent.user_tier).toBe('free');
        expect(signupEvent.user_id).toBe('newuser456');
      });
    });

    it('should track Google signup events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      fireEvent.click(screen.getByTestId('signup-google-btn'));

      await waitFor(() => {
        const signupEvent = mockDataLayer.find(item => item.event === 'user_signup');
        expect(signupEvent).toBeDefined();
        expect(signupEvent.auth_method).toBe('google');
        expect(signupEvent.is_new_user).toBe(true);
      });
    });
  });

  describe('OAuth Flow Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track OAuth completion events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // First login to have a user
      fireEvent.click(screen.getByTestId('login-email-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Complete OAuth
      fireEvent.click(screen.getByTestId('oauth-complete-btn'));

      await waitFor(() => {
        const oauthEvent = mockDataLayer.find(item => item.event === 'oauth_complete');
        expect(oauthEvent).toBeDefined();
        expect(oauthEvent.event_category).toBe('authentication');
        expect(oauthEvent.auth_method).toBe('oauth');
        expect(oauthEvent.user_id).toBe('user123');
      });
    });
  });

  describe('Logout Flow Integration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track logout events with user context', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // First login
      fireEvent.click(screen.getByTestId('login-email-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Then logout
      fireEvent.click(screen.getByTestId('logout-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('idle');
      });

      // Verify logout event
      await waitFor(() => {
        const logoutEvent = mockDataLayer.find(item => item.event === 'user_logout');
        expect(logoutEvent).toBeDefined();
        expect(logoutEvent.event_category).toBe('authentication');
        expect(logoutEvent.user_id).toBe('user123');
      });

      // Should have tracked both login and logout
      expect(screen.getByTestId('total-events')).toHaveTextContent('2');
    });
  });

  describe('Multi-Step Authentication Flows', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should track complete signup to first login journey', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Step 1: Signup
      fireEvent.click(screen.getByTestId('signup-email-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Step 2: Logout
      fireEvent.click(screen.getByTestId('logout-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('idle');
      });

      // Step 3: Login (returning user)
      fireEvent.click(screen.getByTestId('login-email-btn'));
      
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Verify all events were tracked
      await waitFor(() => {
        const events = mockDataLayer.filter(item => 
          ['user_signup', 'user_logout', 'user_login'].includes(item.event)
        );
        expect(events).toHaveLength(3);

        const signupEvent = events.find(e => e.event === 'user_signup');
        const logoutEvent = events.find(e => e.event === 'user_logout');
        const loginEvent = events.find(e => e.event === 'user_login');

        expect(signupEvent.is_new_user).toBe(true);
        expect(loginEvent.is_new_user).toBe(false);
        expect(logoutEvent.user_id).toBe('newuser456');
      });
    });

    it('should track authentication method switching', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Login with email
      fireEvent.click(screen.getByTestId('login-email-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Logout
      fireEvent.click(screen.getByTestId('logout-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('idle');
      });

      // Login with Google
      fireEvent.click(screen.getByTestId('login-google-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Verify both login methods were tracked
      await waitFor(() => {
        const loginEvents = mockDataLayer.filter(item => item.event === 'user_login');
        expect(loginEvents).toHaveLength(2);
        
        const emailLogin = loginEvents.find(e => e.auth_method === 'email');
        const googleLogin = loginEvents.find(e => e.auth_method === 'google');
        
        expect(emailLogin).toBeDefined();
        expect(googleLogin).toBeDefined();
      });
    });
  });

  describe('Event Correlation and Context', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should maintain consistent user context across events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Login and track various events
      fireEvent.click(screen.getByTestId('login-email-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      fireEvent.click(screen.getByTestId('oauth-complete-btn'));
      fireEvent.click(screen.getByTestId('logout-btn'));

      // All events should have consistent user_id when user was logged in
      await waitFor(() => {
        const authEvents = mockDataLayer.filter(item => 
          ['user_login', 'oauth_complete', 'user_logout'].includes(item.event)
        );
        
        authEvents.forEach(event => {
          expect(event.user_id).toBe('user123');
          expect(event.timestamp).toBeDefined();
          expect(event.page_path).toBe('/login');
        });
      });
    });

    it('should enrich events with environment context', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      fireEvent.click(screen.getByTestId('login-email-btn'));

      await waitFor(() => {
        const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(loginEvent).toBeDefined();
        expect(loginEvent.environment).toBe('development');
        expect(loginEvent.page_path).toBe('/login');
        expect(loginEvent.timestamp).toBeDefined();
      });
    });
  });

  describe('Performance and Error Handling', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle rapid authentication events', async () => {
      renderWithProviders(<AuthFlowTestComponent />);

      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
      });

      // Rapid fire multiple auth events
      act(() => {
        fireEvent.click(screen.getByTestId('login-email-btn'));
        fireEvent.click(screen.getByTestId('oauth-complete-btn'));
      });

      await waitFor(() => {
        const authEvents = mockDataLayer.filter(item => 
          ['user_login', 'oauth_complete'].includes(item.event)
        );
        expect(authEvents).toHaveLength(2);
        
        // Events should be properly ordered and timestamped
        authEvents.forEach(event => {
          expect(event.timestamp).toBeDefined();
        });
      });
    });

    it('should maintain event tracking when GTM loads after auth events', async () => {
      // Render without waiting for GTM to load
      renderWithProviders(<AuthFlowTestComponent />);

      // Attempt auth before GTM is ready
      fireEvent.click(screen.getByTestId('login-email-btn'));

      // Wait for both auth and GTM to be ready
      await waitFor(() => {
        expect(screen.getByTestId('gtm-status')).toHaveTextContent('GTM Ready');
        expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      });

      // Event should still be tracked
      await waitFor(() => {
        const loginEvent = mockDataLayer.find(item => item.event === 'user_login');
        expect(loginEvent).toBeDefined();
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});