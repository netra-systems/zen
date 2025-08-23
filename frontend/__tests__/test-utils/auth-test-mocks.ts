// ============================================================================
// AUTHENTICATION TEST MOCKS - COMPREHENSIVE AUTH TESTING INFRASTRUCTURE
// ============================================================================
// This file provides complete authentication mocking for all auth-related tests
// to ensure consistent authentication behavior across all test scenarios.
// ============================================================================

import { createMockUser, createMockAuthConfig } from './comprehensive-test-factories';

export interface MockAuthState {
  isAuthenticated: boolean;
  user: any | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  authConfig: any;
}

export interface MockAuthActions {
  login: jest.Mock;
  logout: jest.Mock;
  refreshToken: jest.Mock;
  clearAuth: jest.Mock;
  setUser: jest.Mock;
  setToken: jest.Mock;
  setLoading: jest.Mock;
  setError: jest.Mock;
}

// ============================================================================
// AUTH STATE FACTORIES
// ============================================================================
export const createAuthenticatedState = (overrides: Partial<MockAuthState> = {}): MockAuthState & MockAuthActions => ({
  // State
  isAuthenticated: true,
  user: createMockUser(),
  token: 'mock-access-token-123',
  loading: false,
  error: null,
  authConfig: createMockAuthConfig(),
  
  // Actions
  login: jest.fn().mockResolvedValue(undefined),
  logout: jest.fn().mockResolvedValue(undefined),
  refreshToken: jest.fn().mockResolvedValue(undefined),
  clearAuth: jest.fn(),
  setUser: jest.fn(),
  setToken: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  
  // Apply overrides
  ...overrides
});

export const createUnauthenticatedState = (overrides: Partial<MockAuthState> = {}): MockAuthState & MockAuthActions => ({
  // State
  isAuthenticated: false,
  user: null,
  token: null,
  loading: false,
  error: null,
  authConfig: createMockAuthConfig(),
  
  // Actions
  login: jest.fn().mockResolvedValue(undefined),
  logout: jest.fn().mockResolvedValue(undefined),
  refreshToken: jest.fn().mockResolvedValue(undefined),
  clearAuth: jest.fn(),
  setUser: jest.fn(),
  setToken: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  
  // Apply overrides
  ...overrides
});

export const createLoadingAuthState = (overrides: Partial<MockAuthState> = {}): MockAuthState & MockAuthActions => ({
  ...createUnauthenticatedState(),
  loading: true,
  ...overrides
});

export const createErrorAuthState = (error: string = 'Authentication failed', overrides: Partial<MockAuthState> = {}): MockAuthState & MockAuthActions => ({
  ...createUnauthenticatedState(),
  error,
  ...overrides
});

// ============================================================================
// AUTH SERVICE MOCK
// ============================================================================
export const createMockAuthService = (initialState: Partial<MockAuthState> = {}) => {
  const state = createAuthenticatedState(initialState);
  
  return {
    // Config management
    getAuthConfig: jest.fn().mockResolvedValue(state.authConfig),
    updateAuthConfig: jest.fn().mockResolvedValue(state.authConfig),
    
    // Token management
    getToken: jest.fn().mockReturnValue(state.token),
    setToken: jest.fn().mockImplementation((token: string) => { state.token = token; }),
    removeToken: jest.fn().mockImplementation(() => { state.token = null; }),
    refreshToken: jest.fn().mockResolvedValue({ access_token: 'refreshed-token', token_type: 'Bearer' }),
    
    // Authentication flow
    handleLogin: jest.fn().mockResolvedValue({ access_token: 'new-token', token_type: 'Bearer' }),
    handleDevLogin: jest.fn().mockResolvedValue({ access_token: 'dev-token', token_type: 'Bearer' }),
    handleLogout: jest.fn().mockResolvedValue(undefined),
    
    // Headers and auth info
    getAuthHeaders: jest.fn().mockReturnValue({ Authorization: `Bearer ${state.token}` }),
    isAuthenticated: jest.fn().mockReturnValue(state.isAuthenticated),
    getCurrentUser: jest.fn().mockReturnValue(state.user),
    
    // Dev mode utilities
    getDevLogoutFlag: jest.fn().mockReturnValue(false),
    setDevLogoutFlag: jest.fn(),
    clearDevLogoutFlag: jest.fn(),
    
    // Hook interface
    useAuth: jest.fn().mockReturnValue(state),
    
    // Internal state for testing
    __getState: () => state,
    __setState: (newState: Partial<MockAuthState>) => Object.assign(state, newState)
  };
};

// ============================================================================
// AUTH CONTEXT MOCK
// ============================================================================
export const createMockAuthContext = (initialState: Partial<MockAuthState> = {}) => {
  const state = createAuthenticatedState(initialState);
  
  return {
    // Context value
    contextValue: state,
    
    // Provider mock
    Provider: ({ children }: { children: React.ReactNode }) => 
      React.createElement('div', { 'data-testid': 'auth-provider' }, children),
    
    // Hook mock
    useAuth: jest.fn().mockReturnValue(state),
    
    // Test utilities
    updateState: (newState: Partial<MockAuthState>) => Object.assign(state, newState),
    simulateLogin: (user = createMockUser()) => {
      Object.assign(state, {
        isAuthenticated: true,
        user,
        token: 'logged-in-token',
        loading: false,
        error: null
      });
    },
    simulateLogout: () => {
      Object.assign(state, {
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: null
      });
    },
    simulateLoading: (loading = true) => {
      state.loading = loading;
    },
    simulateError: (error: string) => {
      Object.assign(state, {
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error
      });
    }
  };
};

// ============================================================================
// AUTH STORE MOCK
// ============================================================================
export const createMockAuthStore = (initialState: Partial<MockAuthState> = {}) => {
  const state = createAuthenticatedState(initialState);
  
  return {
    // Zustand-style selector mock
    useAuthStore: jest.fn().mockImplementation((selector?: (state: any) => any) => {
      if (selector) {
        return selector(state);
      }
      return state;
    }),
    
    // Direct state access
    getState: jest.fn().mockReturnValue(state),
    setState: jest.fn().mockImplementation((updater: any) => {
      if (typeof updater === 'function') {
        Object.assign(state, updater(state));
      } else {
        Object.assign(state, updater);
      }
    }),
    
    // Actions
    actions: {
      login: jest.fn().mockImplementation(async (credentials: any) => {
        state.loading = true;
        // Simulate login
        await new Promise(resolve => setTimeout(resolve, 100));
        Object.assign(state, {
          isAuthenticated: true,
          user: createMockUser({ email: credentials.email }),
          token: 'store-token',
          loading: false,
          error: null
        });
      }),
      logout: jest.fn().mockImplementation(async () => {
        state.loading = true;
        // Simulate logout
        await new Promise(resolve => setTimeout(resolve, 50));
        Object.assign(state, {
          isAuthenticated: false,
          user: null,
          token: null,
          loading: false,
          error: null
        });
      }),
      refreshToken: jest.fn().mockResolvedValue(undefined),
      clearAuth: jest.fn().mockImplementation(() => {
        Object.assign(state, createUnauthenticatedState());
      })
    },
    
    // Test utilities
    __resetState: () => Object.assign(state, createUnauthenticatedState()),
    __setState: (newState: Partial<MockAuthState>) => Object.assign(state, newState)
  };
};

// ============================================================================
// AUTH HOOK MOCKS
// ============================================================================
export const createMockUseAuth = (initialState: Partial<MockAuthState> = {}) => {
  const state = createAuthenticatedState(initialState);
  
  return {
    mockImplementation: jest.fn().mockReturnValue(state),
    updateState: (newState: Partial<MockAuthState>) => Object.assign(state, newState),
    simulateLogin: () => {
      Object.assign(state, {
        isAuthenticated: true,
        user: createMockUser(),
        token: 'hook-token',
        loading: false,
        error: null
      });
    },
    simulateLogout: () => {
      Object.assign(state, createUnauthenticatedState());
    }
  };
};

export const createMockUseAuthState = (initialState: Partial<MockAuthState> = {}) => {
  const state = createAuthenticatedState(initialState);
  
  return {
    mockImplementation: jest.fn().mockReturnValue({
      authState: state,
      isAuthenticated: state.isAuthenticated,
      isLoading: state.loading,
      error: state.error,
      user: state.user,
      token: state.token
    }),
    updateState: (newState: Partial<MockAuthState>) => Object.assign(state, newState)
  };
};

// ============================================================================
// AUTH UTILITIES
// ============================================================================
export const createMockJWT = (payload: any = {}) => {
  const defaultPayload = {
    sub: 'test-user-123',
    email: 'test@example.com',
    name: 'Test User',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour
    ...payload
  };
  
  // Mock JWT - just base64 encode the payload
  const encodedPayload = btoa(JSON.stringify(defaultPayload));
  return `mock-header.${encodedPayload}.mock-signature`;
};

export const createMockAuthHeaders = (token?: string) => ({
  'Authorization': `Bearer ${token || 'mock-token'}`,
  'Content-Type': 'application/json',
  'Accept': 'application/json'
});

export const createMockAuthResponse = (success = true, data: any = {}) => {
  if (success) {
    return {
      status: 200,
      data: {
        access_token: 'mock-access-token',
        token_type: 'Bearer',
        expires_in: 3600,
        user: createMockUser(),
        ...data
      }
    };
  } else {
    return {
      status: 401,
      data: {
        error: 'Authentication failed',
        message: 'Invalid credentials',
        ...data
      }
    };
  }
};

// ============================================================================
// AUTH FLOW SIMULATION
// ============================================================================
export const simulateAuthFlow = (mockAuthService: any) => ({
  login: async (email = 'test@example.com', password = 'password123') => {
    mockAuthService.__setState({ loading: true });
    await new Promise(resolve => setTimeout(resolve, 100));
    mockAuthService.__setState({
      isAuthenticated: true,
      user: createMockUser({ email }),
      token: 'flow-token',
      loading: false,
      error: null
    });
  },
  
  logout: async () => {
    mockAuthService.__setState({ loading: true });
    await new Promise(resolve => setTimeout(resolve, 50));
    mockAuthService.__setState(createUnauthenticatedState());
  },
  
  refreshToken: async () => {
    const newToken = 'refreshed-flow-token';
    mockAuthService.__setState({ token: newToken });
    return newToken;
  },
  
  simulateTokenExpiration: () => {
    mockAuthService.__setState({
      isAuthenticated: false,
      token: null,
      error: 'Token expired'
    });
  },
  
  simulateNetworkError: () => {
    mockAuthService.__setState({
      loading: false,
      error: 'Network error - unable to authenticate'
    });
  }
});

// ============================================================================
// AUTH TEST SCENARIOS
// ============================================================================
export const authTestScenarios = {
  // Successful authentication
  successfulLogin: () => ({
    authState: createAuthenticatedState(),
    mockResponses: [createMockAuthResponse(true)]
  }),
  
  // Failed authentication
  failedLogin: () => ({
    authState: createErrorAuthState('Invalid credentials'),
    mockResponses: [createMockAuthResponse(false, { error: 'Invalid credentials' })]
  }),
  
  // Loading state
  loadingAuth: () => ({
    authState: createLoadingAuthState(),
    mockResponses: []
  }),
  
  // Token refresh
  tokenRefresh: () => ({
    authState: createAuthenticatedState({ token: 'refreshed-token' }),
    mockResponses: [createMockAuthResponse(true, { access_token: 'refreshed-token' })]
  }),
  
  // Session timeout
  sessionTimeout: () => ({
    authState: createErrorAuthState('Session expired'),
    mockResponses: [createMockAuthResponse(false, { error: 'Session expired' })]
  }),
  
  // Network error
  networkError: () => ({
    authState: createErrorAuthState('Network error'),
    mockResponses: []
  })
};

export default {
  createAuthenticatedState,
  createUnauthenticatedState,
  createMockAuthService,
  createMockAuthContext,
  createMockAuthStore,
  authTestScenarios
};