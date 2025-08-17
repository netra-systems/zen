/**
 * Mock data definitions for ChatHistorySection tests
 * Provides consistent test data and mock implementations
 */

// Sample mock threads for testing
export const mockThreads = [
  {
    id: 'thread-1',
    title: 'First Conversation',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    user_id: 'user-1',
    message_count: 5,
    status: 'active' as const,
  },
  {
    id: 'thread-2',
    title: 'Second Conversation',
    created_at: Math.floor((Date.now() - 86400000) / 1000), // Yesterday
    updated_at: Math.floor((Date.now() - 86400000) / 1000),
    user_id: 'user-1',
    message_count: 3,
    status: 'active' as const,
  },
  {
    id: 'thread-3',
    title: 'Third Conversation',
    created_at: Math.floor((Date.now() - 604800000) / 1000), // Week ago
    updated_at: Math.floor((Date.now() - 604800000) / 1000),
    user_id: 'user-1',
    message_count: 10,
    status: 'active' as const,
  },
];

// Mock router instance
export const mockRouter = {
  push: jest.fn(),
};

// Mock pathname
export const mockPathname = '/chat';

// Helper to create mock thread with overrides
export const createMockThread = (overrides: Partial<typeof mockThreads[0]> = {}) => {
  return {
    id: `thread-${Math.random().toString(36).substr(2, 9)}`,
    title: 'Test Conversation',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    user_id: 'user-1',
    message_count: 0,
    status: 'active' as const,
    ...overrides,
  };
};