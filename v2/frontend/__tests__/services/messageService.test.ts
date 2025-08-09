import { messageService } from '@/services/messageService';
import { Message } from '@/types/chat';

// Mock fetch
global.fetch = jest.fn();

describe('MessageService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('Thread Management', () => {
    it('should create a new thread', async () => {
      const mockThread = {
        id: 'thread-123',
        created_at: Date.now(),
        metadata_: { user_id: 'user-123' }
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockThread,
      });

      const result = await messageService.createThread('user-123');

      expect(fetch).toHaveBeenCalledWith('/api/threads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': expect.any(String),
        },
        body: JSON.stringify({ user_id: 'user-123' }),
      });

      expect(result).toEqual(mockThread);
    });

    it('should fetch threads for a user', async () => {
      const mockThreads = [
        { id: 'thread-1', created_at: 123456 },
        { id: 'thread-2', created_at: 123457 },
      ];

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockThreads,
      });

      const result = await messageService.getThreads('user-123');

      expect(fetch).toHaveBeenCalledWith(
        '/api/threads?user_id=user-123',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': expect.any(String),
          }),
        })
      );

      expect(result).toEqual(mockThreads);
    });

    it('should handle thread fetch errors', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(messageService.getThreads('user-123')).rejects.toThrow('Network error');
    });
  });

  describe('Message Persistence', () => {
    it('should save a message to the server', async () => {
      const message: Message = {
        id: 'msg-123',
        role: 'user',
        content: 'Test message',
        timestamp: new Date().toISOString(),
        displayed_to_user: true,
      };

      const savedMessage = { ...message, persisted: true };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => savedMessage,
      });

      const result = await messageService.saveMessage('thread-123', message);

      expect(fetch).toHaveBeenCalledWith('/api/threads/thread-123/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': expect.any(String),
        },
        body: JSON.stringify(message),
      });

      expect(result).toEqual(savedMessage);
    });

    it('should fetch messages for a thread', async () => {
      const mockMessages: Message[] = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Hello',
          timestamp: '2023-01-01T00:00:00Z',
          displayed_to_user: true,
        },
        {
          id: 'msg-2',
          role: 'assistant',
          content: 'Hi there!',
          timestamp: '2023-01-01T00:00:01Z',
          displayed_to_user: true,
        },
      ];

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMessages,
      });

      const result = await messageService.getThreadMessages('thread-123');

      expect(fetch).toHaveBeenCalledWith(
        '/api/threads/thread-123/messages',
        expect.objectContaining({
          method: 'GET',
        })
      );

      expect(result).toEqual(mockMessages);
    });

    it('should handle pagination for large message lists', async () => {
      const mockMessages = Array(100).fill(0).map((_, i) => ({
        id: `msg-${i}`,
        role: i % 2 === 0 ? 'user' : 'assistant',
        content: `Message ${i}`,
        timestamp: new Date(Date.now() + i * 1000).toISOString(),
        displayed_to_user: true,
      }));

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          messages: mockMessages.slice(0, 50),
          has_more: true,
          next_cursor: 'cursor-50',
        }),
      });

      const result = await messageService.getThreadMessages('thread-123', {
        limit: 50,
      });

      expect(fetch).toHaveBeenCalledWith(
        '/api/threads/thread-123/messages?limit=50',
        expect.any(Object)
      );

      expect(result.messages).toHaveLength(50);
      expect(result.has_more).toBe(true);
      expect(result.next_cursor).toBe('cursor-50');
    });
  });

  describe('Local Cache Management', () => {
    it('should cache messages locally', async () => {
      const messages: Message[] = [
        {
          id: 'msg-1',
          role: 'user',
          content: 'Cached message',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
      ];

      await messageService.cacheMessages('thread-123', messages);

      const cached = await messageService.getCachedMessages('thread-123');
      expect(cached).toEqual(messages);
    });

    it('should sync local cache with server', async () => {
      const localMessages: Message[] = [
        {
          id: 'msg-local-1',
          role: 'user',
          content: 'Local message',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
          local: true,
        },
      ];

      const serverMessages: Message[] = [
        {
          id: 'msg-server-1',
          role: 'assistant',
          content: 'Server message',
          timestamp: new Date().toISOString(),
          displayed_to_user: true,
        },
      ];

      await messageService.cacheMessages('thread-123', localMessages);

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => serverMessages,
      });

      const synced = await messageService.syncMessages('thread-123');

      // Should merge local and server messages
      expect(synced).toHaveLength(2);
      expect(synced.some(m => m.id === 'msg-local-1')).toBe(true);
      expect(synced.some(m => m.id === 'msg-server-1')).toBe(true);
    });

    it('should handle offline mode', async () => {
      const message: Message = {
        id: 'msg-offline',
        role: 'user',
        content: 'Offline message',
        timestamp: new Date().toISOString(),
        displayed_to_user: true,
      };

      // Simulate offline - fetch fails
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      // Should queue message for later
      const result = await messageService.saveMessage('thread-123', message, {
        offline: true,
      });

      expect(result.queued).toBe(true);
      expect(result.message).toEqual(message);

      // Check if queued
      const queued = await messageService.getQueuedMessages();
      expect(queued).toContainEqual(expect.objectContaining({
        message,
        thread_id: 'thread-123',
      }));
    });

    it('should retry failed message sends', async () => {
      const message: Message = {
        id: 'msg-retry',
        role: 'user',
        content: 'Retry message',
        timestamp: new Date().toISOString(),
        displayed_to_user: true,
      };

      // First attempt fails
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await messageService.saveMessage('thread-123', message, {
        offline: true,
      });

      // Now simulate coming back online
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...message, persisted: true }),
      });

      const retryResults = await messageService.retryQueuedMessages();

      expect(retryResults.successful).toBe(1);
      expect(retryResults.failed).toBe(0);
      expect(fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Thread State Management', () => {
    it('should save thread state', async () => {
      const threadState = {
        thread_id: 'thread-123',
        last_message_id: 'msg-100',
        unread_count: 5,
        metadata: { last_active: Date.now() },
      };

      await messageService.saveThreadState(threadState);

      const retrieved = await messageService.getThreadState('thread-123');
      expect(retrieved).toEqual(threadState);
    });

    it('should update thread metadata', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true }),
      });

      await messageService.updateThreadMetadata('thread-123', {
        title: 'Updated thread title',
        tags: ['important', 'work'],
      });

      expect(fetch).toHaveBeenCalledWith(
        '/api/threads/thread-123/metadata',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            title: 'Updated thread title',
            tags: ['important', 'work'],
          }),
        })
      );
    });
  });
});