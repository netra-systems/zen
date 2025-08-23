/**
 * Test Data Builders
 * Builder pattern for creating consistent test data
 */

export const createMockUser = (overrides = {}) => ({
  id: 'test-user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  name: 'Test User',
  ...overrides
});

export const createMockToken = (): string => 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature';

export const createMockMessage = (overrides = {}) => ({
  id: Date.now().toString(),
  content: 'Test message',
  role: 'user' as const,
  timestamp: new Date().toISOString(),
  ...overrides
});

export const createMockThread = (overrides = {}) => ({
  id: Date.now().toString(),
  title: 'Test Thread',
  created_at: Date.now(),
  ...overrides
});

export const createWebSocketMessage = (type: string, data = {}) => 
  JSON.stringify({ type, ...data });

export const createAuthenticatedRequest = (url: string, options: RequestInit = {}) => {
  const authToken = createMockToken();
  return {
    url,
    options: {
      ...options,
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    }
  };
};

export const createMockAuthResponse = (overrides = {}) => ({
  token: createMockToken(),
  user: createMockUser(),
  access_token: createMockToken(),
  token_type: 'Bearer',
  ...overrides
});

export const createStreamChunk = (chunk: string) =>
  createWebSocketMessage('stream_chunk', { chunk });

export const createAgentMessage = (content: string) =>
  createWebSocketMessage('agent_message', { content });