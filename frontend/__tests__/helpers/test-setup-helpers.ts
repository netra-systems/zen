/**
 * Test Setup Helpers
 * Utilities for setting up test data, mocks, and state
 */

export function createTestUser() {
  return {
    id: 'test-user-123',
    email: 'test@example.com',
    name: 'Test User',
    avatar: null,
    created_at: new Date().toISOString(),
  };
}

export function createMockToken() {
  return 'mock-jwt-token-' + Date.now();
}

export function setAuthenticatedState() {
  // Mock authenticated state
  const mockUser = createTestUser();
  const mockToken = createMockToken();
  
  // Set up store state if needed
  if (typeof window !== 'undefined') {
    localStorage.setItem('auth_token', mockToken);
    localStorage.setItem('user', JSON.stringify(mockUser));
  }
  
  return { user: mockUser, token: mockToken };
}

export function setupMockFetchForConfig() {
  const mockConfig = {
    google_client_id: 'mock-google-client-id',
    development_mode: true,
    endpoints: {
      auth: 'http://localhost:8001',
      api: 'http://localhost:8000',
    },
  };

  (global.fetch as jest.Mock) = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockConfig),
      text: () => Promise.resolve(JSON.stringify(mockConfig)),
    })
  );

  return mockConfig;
}

export function createMockOAuthResponse() {
  return {
    access_token: 'oauth-token',
    refresh_token: 'refresh-token',
    token_type: 'Bearer',
    expires_in: 3600,
    user: createTestUser(),
  };
}

export async function simulateOAuthCallback(code: string) {
  const mockResponse = createMockOAuthResponse();
  
  (global.fetch as jest.Mock) = jest.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
  );

  return mockResponse;
}

export function assertUserIsAuthenticated() {
  // Add assertions for authenticated state
  expect(localStorage.getItem('auth_token')).toBeTruthy();
  expect(localStorage.getItem('user')).toBeTruthy();
}

export function setupPersistedAuthState(user: any, token: string) {
  localStorage.setItem('auth_token', token);
  localStorage.setItem('user', JSON.stringify(user));
}

export function resetTestStores() {
  // Clear localStorage
  localStorage.clear();
  
  // Reset any store states if needed
  jest.clearAllMocks();
}

export function simulateSessionRestore() {
  // Simulate app startup with persisted auth
  const token = localStorage.getItem('auth_token');
  const user = localStorage.getItem('user');
  
  return {
    token,
    user: user ? JSON.parse(user) : null,
  };
}