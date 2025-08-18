/**
 * REVENUE-CRITICAL TESTS: Thread Management Service
 * BVJ: All segments - Thread failures = 30% retention impact
 * Tests core user workflow reliability that drives Free→Paid conversion
 */

import { ThreadService } from '@/services/threadService';
import { ThreadMetadata } from '@/types/registry';
import {
  createMockThread,
  createMockThreads,
  createMockMessagesResponse,
  createApiError,
  expectListCall,
  expectGetCall,
  expectCreateCall,
  expectUpdateCall,
  expectDeleteCall,
  expectMessagesCall,
  expectMixedConcurrentResults,
  TEST_METADATA,
  URGENT_METADATA
} from './threadService-helpers';

// Mock apiClient before importing
jest.mock('@/services/apiClientWrapper', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}));

import { apiClient } from '@/services/apiClientWrapper';

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('ThreadService Revenue-Critical Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Thread Listing - User Activation Critical', () => {
    test('lists threads with default pagination', async () => {
      const mockThreads = createMockThreads(2);
      mockApiClient.get.mockResolvedValue({ data: mockThreads });

      const result = await ThreadService.listThreads();

      expectListCall(mockApiClient, 20, 0);
      expect(result).toEqual(mockThreads);
    });

    test('lists threads with custom pagination', async () => {
      const mockThreads = createMockThreads(5);
      mockApiClient.get.mockResolvedValue({ data: mockThreads });

      const result = await ThreadService.listThreads(5, 10);

      expectListCall(mockApiClient, 5, 10);
      expect(result).toEqual(mockThreads);
    });

    test('handles empty thread list for new users', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] });

      const result = await ThreadService.listThreads();

      expect(result).toEqual([]);
      expectListCall(mockApiClient, 20, 0);
    });

    test('handles pagination with zero limit edge case', async () => {
      mockApiClient.get.mockResolvedValue({ data: [] });

      const result = await ThreadService.listThreads(0, 0);

      expectListCall(mockApiClient, 0, 0);
      expect(result).toEqual([]);
    });

    test('throws on list API failures', async () => {
      mockApiClient.get.mockRejectedValue(createApiError(500, 'Server Error'));

      await expect(ThreadService.listThreads()).rejects.toThrow('Server Error');
    });
  });

  describe('Thread Retrieval - Returning User Flow', () => {
    test('retrieves specific thread successfully', async () => {
      const mockThread = createMockThread('thread-1', 'Important Chat');
      mockApiClient.get.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.getThread('thread-1');

      expectGetCall(mockApiClient, 'thread-1');
      expect(result).toEqual(mockThread);
    });

    test('handles thread not found gracefully', async () => {
      mockApiClient.get.mockRejectedValue(createApiError(404, 'Thread not found'));

      await expect(ThreadService.getThread('nonexistent')).rejects.toThrow('Thread not found');
    });

    test('handles malformed thread ID', async () => {
      mockApiClient.get.mockRejectedValue(createApiError(400, 'Invalid thread ID'));

      await expect(ThreadService.getThread('')).rejects.toThrow('Invalid thread ID');
    });
  });

  describe('Thread Creation - Activation Moment', () => {
    test('creates thread with title only', async () => {
      const mockThread = createMockThread('new-id', 'New Chat');
      mockApiClient.post.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.createThread('New Chat');

      expectCreateCall(mockApiClient, { name: 'New Chat', title: 'New Chat', metadata: undefined });
      expect(result).toEqual(mockThread);
    });

    test('creates thread with title and metadata', async () => {
      const mockThread = createMockThread('new-id', 'Priority Chat');
      mockApiClient.post.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.createThread('Priority Chat', TEST_METADATA);

      expectCreateCall(mockApiClient, { 
        name: 'Priority Chat', 
        title: 'Priority Chat', 
        metadata: TEST_METADATA 
      });
      expect(result).toEqual(mockThread);
    });

    test('creates thread without title', async () => {
      const mockThread = createMockThread('new-id', '');
      mockApiClient.post.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.createThread();

      expectCreateCall(mockApiClient, { name: undefined, title: undefined, metadata: undefined });
      expect(result).toEqual(mockThread);
    });

    test('handles creation failures', async () => {
      mockApiClient.post.mockRejectedValue(createApiError(400, 'Validation failed'));

      await expect(ThreadService.createThread('Test')).rejects.toThrow('Validation failed');
    });
  });

  describe('Thread Updates - User Engagement', () => {
    test('updates thread title', async () => {
      const mockThread = createMockThread('thread-1', 'Updated Title');
      mockApiClient.put.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.updateThread('thread-1', 'Updated Title');

      expectUpdateCall(mockApiClient, 'thread-1', { 
        name: 'Updated Title', 
        title: 'Updated Title', 
        metadata: undefined 
      });
      expect(result).toEqual(mockThread);
    });

    test('updates thread with metadata only', async () => {
      const metadata: ThreadMetadata = { bookmarked: true };
      const mockThread = createMockThread('thread-1', 'Original');
      mockApiClient.put.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.updateThread('thread-1', undefined, metadata);

      expectUpdateCall(mockApiClient, 'thread-1', { 
        name: undefined, 
        title: undefined, 
        metadata 
      });
      expect(result).toEqual(mockThread);
    });

    test('updates thread with both title and metadata', async () => {
      const mockThread = createMockThread('thread-1', 'Urgent Task');
      mockApiClient.put.mockResolvedValue({ data: mockThread });

      const result = await ThreadService.updateThread('thread-1', 'Urgent Task', URGENT_METADATA);

      expectUpdateCall(mockApiClient, 'thread-1', { 
        name: 'Urgent Task', 
        title: 'Urgent Task', 
        metadata: URGENT_METADATA 
      });
      expect(result).toEqual(mockThread);
    });

    test('handles update failures', async () => {
      mockApiClient.put.mockRejectedValue(createApiError(403, 'Access denied'));

      await expect(ThreadService.updateThread('thread-1', 'New Title')).rejects.toThrow('Access denied');
    });
  });

  describe('Thread Deletion - Data Integrity', () => {
    test('deletes thread successfully', async () => {
      mockApiClient.delete.mockResolvedValue({ data: undefined });

      await ThreadService.deleteThread('thread-1');

      expectDeleteCall(mockApiClient, 'thread-1');
    });

    test('handles deletion of non-existent thread', async () => {
      mockApiClient.delete.mockRejectedValue(createApiError(404, 'Thread not found'));

      await expect(ThreadService.deleteThread('nonexistent')).rejects.toThrow('Thread not found');
    });

    test('handles deletion permissions error', async () => {
      mockApiClient.delete.mockRejectedValue(createApiError(403, 'Permission denied'));

      await expect(ThreadService.deleteThread('thread-1')).rejects.toThrow('Permission denied');
    });
  });

  describe('Thread Messages - Content Loading Critical', () => {
    test('retrieves messages with default pagination', async () => {
      const mockResponse = createMockMessagesResponse('thread-1', 3);
      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await ThreadService.getThreadMessages('thread-1');

      expectMessagesCall(mockApiClient, 'thread-1', 50, 0);
      expect(result).toEqual(mockResponse);
    });

    test('retrieves messages with custom pagination', async () => {
      const mockResponse = createMockMessagesResponse('thread-1', 2);
      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await ThreadService.getThreadMessages('thread-1', 10, 20);

      expectMessagesCall(mockApiClient, 'thread-1', 10, 20);
      expect(result).toEqual(mockResponse);
    });

    test('handles empty message history', async () => {
      const mockResponse = createMockMessagesResponse('thread-1', 0);
      mockApiClient.get.mockResolvedValue({ data: mockResponse });

      const result = await ThreadService.getThreadMessages('thread-1');

      expect(result.messages).toEqual([]);
      expect(result.total).toBe(0);
    });

    test('handles messages API failures', async () => {
      mockApiClient.get.mockRejectedValue(createApiError(500, 'Messages unavailable'));

      await expect(ThreadService.getThreadMessages('thread-1')).rejects.toThrow('Messages unavailable');
    });
  });

  describe('Concurrent Operations - System Resilience', () => {
    test('handles multiple thread operations simultaneously', async () => {
      const mockThreads = createMockThreads(3);
      mockApiClient.get.mockResolvedValue({ data: mockThreads });
      mockApiClient.post.mockResolvedValue({ data: mockThreads[0] });
      mockApiClient.put.mockResolvedValue({ data: mockThreads[1] });

      const [listResult, createResult, updateResult] = await Promise.all([
        ThreadService.listThreads(),
        ThreadService.createThread('New Thread'),
        ThreadService.updateThread('thread-1', 'Updated')
      ]);

      expect(listResult).toEqual(mockThreads);
      expect(createResult).toEqual(mockThreads[0]);
      expect(updateResult).toEqual(mockThreads[1]);
    });

    test('isolates failures in concurrent operations', async () => {
      mockApiClient.get.mockResolvedValue({ data: createMockThreads(1) });
      mockApiClient.post.mockRejectedValue(createApiError(400, 'Create failed'));
      mockApiClient.put.mockResolvedValue({ data: createMockThread('1', 'Updated') });

      const results = await Promise.allSettled([
        ThreadService.listThreads(),
        ThreadService.createThread('Bad Thread'),
        ThreadService.updateThread('thread-1', 'Good Update')
      ]);

      expectMixedConcurrentResults(results);
    });
  });
});

// All helper functions moved to threadService-helpers.ts for modular architecture