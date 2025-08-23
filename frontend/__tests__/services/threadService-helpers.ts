/**
 * Thread Service Test Helpers
 * Provides utilities for testing ThreadService functionality
 */

import { ThreadMetadata } from '@/types/unified';

// Test data constants
export const TEST_METADATA: ThreadMetadata = {
  title: 'Test Thread',
  renamed: false,
  tags: ['test'],
  priority: 'normal',
  participants: ['user1'],
  context: {},
  attachments: []
};

export const URGENT_METADATA: ThreadMetadata = {
  title: 'Urgent Thread',
  renamed: true,
  tags: ['urgent', 'important'],
  priority: 'high',
  participants: ['user1', 'user2'],
  context: { urgency: 'high' },
  attachments: []
};

// Mock response creators
export function createMockThread(id: string = 'thread-1', metadata?: Partial<ThreadMetadata>) {
  return {
    id,
    created_at: Date.now(),
    updated_at: Date.now(),
    message_count: 0,
    metadata: {
      ...TEST_METADATA,
      ...metadata
    }
  };
}

export function createMockThreads(count: number = 5): any[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `thread-${i + 1}`,
    created_at: Date.now() - (i * 1000 * 60),
    updated_at: Date.now() - (i * 1000 * 30),
    message_count: i * 2,
    metadata: {
      title: `Thread ${i + 1}`,
      renamed: i % 2 === 0,
      tags: i % 3 === 0 ? ['important'] : [],
      priority: 'normal',
      participants: [`user${i + 1}`],
      context: {},
      attachments: []
    }
  }));
}

export function createMockMessagesResponse(threadId: string, count: number = 10) {
  return {
    messages: Array.from({ length: count }, (_, i) => ({
      id: `msg-${i + 1}`,
      thread_id: threadId,
      content: `Message ${i + 1}`,
      role: i % 2 === 0 ? 'user' : 'assistant',
      timestamp: Date.now() - (i * 1000),
      metadata: {}
    })),
    has_more: count >= 10,
    next_cursor: count >= 10 ? `cursor-${count}` : null
  };
}

// Expectation helpers for apiClient (not fetch)
export function expectListCall(mockApiClient: any, limit: number, offset: number) {
  expect(mockApiClient.get).toHaveBeenCalledWith(
    expect.stringContaining('/threads'),
    expect.objectContaining({
      params: { limit, offset }
    })
  );
}

export function expectCreateCall(mockApiClient: any, expectedMetadata: ThreadMetadata) {
  expect(mockApiClient.post).toHaveBeenCalledWith(
    expect.stringContaining('/threads'),
    { metadata: expectedMetadata }
  );
}

export function expectGetCall(mockApiClient: any, threadId: string) {
  expect(mockApiClient.get).toHaveBeenCalledWith(
    expect.stringContaining(`/threads/${threadId}`)
  );
}

export function expectUpdateCall(mockApiClient: any, threadId: string, metadata: ThreadMetadata) {
  expect(mockApiClient.put).toHaveBeenCalledWith(
    expect.stringContaining(`/threads/${threadId}`),
    { metadata }
  );
}

export function expectDeleteCall(mockApiClient: any, threadId: string) {
  expect(mockApiClient.delete).toHaveBeenCalledWith(
    expect.stringContaining(`/threads/${threadId}`)
  );
}

export function expectMessagesCall(mockApiClient: any, threadId: string, limit?: number, cursor?: string) {
  const expectedParams: any = {};
  if (limit) expectedParams.limit = limit;
  if (cursor) expectedParams.cursor = cursor;
  
  expect(mockApiClient.get).toHaveBeenCalledWith(
    expect.stringContaining(`/threads/${threadId}/messages`),
    Object.keys(expectedParams).length > 0 ? expect.objectContaining({ params: expectedParams }) : undefined
  );
}

// Concurrent operation helpers
export function expectMixedConcurrentResults(results: any[]) {
  // Verify all results are resolved
  expect(results).toHaveLength(results.length);
  
  // Check for no duplicate IDs
  const ids = results.map(r => r.id).filter(Boolean);
  expect(new Set(ids).size).toBe(ids.length);
  
  // Verify structure of results
  results.forEach(result => {
    if (result.id) {
      expect(result).toHaveProperty('created_at');
      expect(result).toHaveProperty('metadata');
    }
  });
}

// Mock setup helpers
export function setupThreadServiceMocks(mockFetch: jest.Mock) {
  // Default successful responses
  mockFetch.mockImplementation(async (url: string, options: any) => {
    const method = options?.method || 'GET';
    
    if (url.includes('/threads') && method === 'POST') {
      return {
        ok: true,
        json: async () => createMockThread('new-thread-id', JSON.parse(options.body).metadata)
      };
    }
    
    if (url.match(/\/threads\/[^\/]+$/) && method === 'GET') {
      const threadId = url.split('/').pop();
      return {
        ok: true,
        json: async () => createMockThread(threadId!)
      };
    }
    
    if (url.includes('/threads') && method === 'GET') {
      return {
        ok: true,
        json: async () => ({ threads: createMockThreads() })
      };
    }
    
    if (url.includes('/messages')) {
      const threadId = url.split('/')[url.split('/').indexOf('threads') + 1];
      return {
        ok: true,
        json: async () => createMockMessagesResponse(threadId)
      };
    }
    
    if (method === 'DELETE') {
      return { ok: true, json: async () => ({}) };
    }
    
    if (method === 'PATCH') {
      const threadId = url.split('/').pop();
      return {
        ok: true,
        json: async () => createMockThread(threadId!, JSON.parse(options.body).metadata)
      };
    }
    
    return { ok: false, status: 404, json: async () => ({ error: 'Not found' }) };
  });
}

// Error creation helper
export function createApiError(status: number, message: string) {
  const error: any = new Error(message);
  error.response = {
    status,
    data: { error: message }
  };
  return error;
}

// Error scenario helpers
export function setupErrorScenario(mockFetch: jest.Mock, errorType: 'network' | 'server' | 'auth') {
  switch (errorType) {
    case 'network':
      mockFetch.mockRejectedValue(new Error('Network error'));
      break;
    case 'server':
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal server error' })
      });
      break;
    case 'auth':
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized' })
      });
      break;
  }
}