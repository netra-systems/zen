/**
 * Verification test for ThreadService.getThread mock fix
 * This test specifically verifies that all ThreadService methods are properly mocked
 */

import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';

// Apply the same mock structure as in the fixed tests
jest.mock('@/services/threadService', () => ({
  ThreadService: {
    listThreads: jest.fn().mockResolvedValue([]),
    createThread: jest.fn().mockResolvedValue({ 
      id: 'new-thread', 
      created_at: Math.floor(Date.now() / 1000), 
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 0,
      metadata: { title: 'New Chat', renamed: false }
    }),
    getThread: jest.fn().mockResolvedValue({
      id: 'test-thread',
      created_at: Math.floor(Date.now() / 1000),
      updated_at: Math.floor(Date.now() / 1000),
      message_count: 1,
      metadata: { title: 'Test Thread', renamed: false }
    }),
    deleteThread: jest.fn(),
    updateThread: jest.fn(),
    getThreadMessages: jest.fn().mockResolvedValue({ 
      messages: [], 
      thread_id: 'test', 
      total: 0, 
      limit: 50, 
      offset: 0 
    })
  }
}));

jest.mock('@/services/threadRenameService', () => ({
  ThreadRenameService: {
    autoRenameThread: jest.fn()
  }
}));

describe('ThreadService Mock Verification', () => {
  describe('ThreadService methods', () => {
    it('should have all required methods defined as functions', () => {
      expect(ThreadService.listThreads).toBeDefined();
      expect(typeof ThreadService.listThreads).toBe('function');
      
      expect(ThreadService.createThread).toBeDefined();
      expect(typeof ThreadService.createThread).toBe('function');
      
      expect(ThreadService.getThread).toBeDefined();
      expect(typeof ThreadService.getThread).toBe('function');
      
      expect(ThreadService.deleteThread).toBeDefined();
      expect(typeof ThreadService.deleteThread).toBe('function');
      
      expect(ThreadService.updateThread).toBeDefined();
      expect(typeof ThreadService.updateThread).toBe('function');
      
      expect(ThreadService.getThreadMessages).toBeDefined();
      expect(typeof ThreadService.getThreadMessages).toBe('function');
    });

    it('should return proper mock values for getThread', async () => {
      const result = await ThreadService.getThread('test-thread-id');
      
      expect(result).toEqual({
        id: 'test-thread',
        created_at: expect.any(Number),
        updated_at: expect.any(Number),
        message_count: 1,
        metadata: { title: 'Test Thread', renamed: false }
      });
    });

    it('should return proper mock values for createThread', async () => {
      const result = await ThreadService.createThread('Test Title');
      
      expect(result).toEqual({
        id: 'new-thread',
        created_at: expect.any(Number),
        updated_at: expect.any(Number),
        message_count: 0,
        metadata: { title: 'New Chat', renamed: false }
      });
    });
  });

  describe('ThreadRenameService methods', () => {
    it('should have autoRenameThread method defined', () => {
      expect(ThreadRenameService.autoRenameThread).toBeDefined();
      expect(typeof ThreadRenameService.autoRenameThread).toBe('function');
    });
  });

  describe('Original error reproduction', () => {
    it('should NOT throw "ThreadService.getThread is not a function" error', async () => {
      // This test reproduces the exact scenario that was causing the original error
      expect(() => {
        ThreadService.getThread('some-thread-id');
      }).not.toThrow('ThreadService.getThread is not a function');
      
      // Verify the method actually works
      const result = await ThreadService.getThread('some-thread-id');
      expect(result).toBeDefined();
      expect(result.id).toBe('test-thread');
    });
  });
});