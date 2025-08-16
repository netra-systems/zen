/**
 * Test Data Builders
 * Builder pattern for creating consistent test data
 */

export const createMockUser = (overrides = {}) => ({
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  ...overrides
});

export const createMockToken = (): string => 'test-jwt-token';

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

export const createStreamChunk = (chunk: string) =>
  createWebSocketMessage('stream_chunk', { chunk });

export const createAgentMessage = (content: string) =>
  createWebSocketMessage('agent_message', { content });