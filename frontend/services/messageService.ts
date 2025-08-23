import { Message } from '@/types/unified';
import { Thread } from '@/types/unified';
import { authInterceptor } from '@/lib/auth-interceptor';
import { logger } from '@/lib/logger';

interface PaginatedMessages {
  messages: Message[];
  has_more: boolean;
  next_cursor?: string;
}

interface QueuedMessage {
  message: Message;
  thread_id: string;
  timestamp: number;
}

interface MessageThreadState {
  thread_id: string;
  last_message_id: string;
  unread_count: number;
  metadata: any;
}

interface SaveMessageOptions {
  offline?: boolean;
}

interface GetMessagesOptions {
  limit?: number;
  cursor?: string;
}

class MessageService {
  private queuedMessages: QueuedMessage[] = [];
  private threadStates: Map<string, MessageThreadState> = new Map();

  // Auth header method kept for backward compatibility but deprecated
  // Auth is now handled by authInterceptor
  private getAuthHeader(): string {
    const token = localStorage.getItem('jwt_token') || '';
    return `Bearer ${token}`;
  }

  // Thread Management
  async createThread(userId: string): Promise<Thread> {
    try {
      const response = await authInterceptor.post('/api/threads', { user_id: userId });
      
      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage: string;
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.detail || parsed.message || parsed.error || `Failed to create thread: ${response.statusText}`;
        } catch {
          errorMessage = errorData || `Failed to create thread: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      return response.json();
    } catch (error) {
      logger.error('Failed to create thread', error as Error, {
        component: 'MessageService',
        action: 'createThread',
        userId
      });
      throw error;
    }
  }

  async getThreads(userId: string): Promise<Thread[]> {
    try {
      const response = await authInterceptor.get(`/api/threads?user_id=${userId}`);
      
      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage: string;
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.detail || parsed.message || parsed.error || `Failed to fetch threads: ${response.statusText}`;
        } catch {
          errorMessage = errorData || `Failed to fetch threads: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      return response.json();
    } catch (error) {
      logger.error('Failed to fetch threads', error as Error, {
        component: 'MessageService',
        action: 'getThreads',
        userId
      });
      throw error;
    }
  }

  // Message Persistence
  async saveMessage(
    threadId: string,
    message: Message,
    options: SaveMessageOptions = {}
  ): Promise<any> {
    if (options.offline) {
      // Queue for later when offline
      this.queuedMessages.push({
        message,
        thread_id: threadId,
        timestamp: Date.now(),
      });

      return {
        queued: true,
        message,
      };
    }

    try {
      const response = await authInterceptor.post(`/api/threads/${threadId}/messages`, message);
      
      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage: string;
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.detail || parsed.message || parsed.error || `Failed to save message: ${response.statusText}`;
        } catch {
          errorMessage = errorData || `Failed to save message: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      
      return response.json();
    } catch (error) {
      logger.error('Failed to save message', error as Error, {
        component: 'MessageService',
        action: 'saveMessage',
        threadId
      });
      throw error;
    }
  }

  async getThreadMessages(
    threadId: string,
    options: GetMessagesOptions = {}
  ): Promise<Message[] | PaginatedMessages> {
    const params = new URLSearchParams();
    if (options.limit) {
      params.append('limit', options.limit.toString());
    }
    if (options.cursor) {
      params.append('cursor', options.cursor);
    }

    const url = params.toString()
      ? `/api/threads/${threadId}/messages?${params}`
      : `/api/threads/${threadId}/messages`;

    try {
      const response = await authInterceptor.get(url);
      
      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage: string;
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.detail || parsed.message || parsed.error || `Failed to fetch messages: ${response.statusText}`;
        } catch {
          errorMessage = errorData || `Failed to fetch messages: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
      
      const data = await response.json();
      
      // Handle both paginated and non-paginated responses
      if (options.limit && data.messages) {
        return data;
      }
      
      return data.messages || data;
    } catch (error) {
      logger.error('Failed to fetch messages', error as Error, {
        component: 'MessageService',
        action: 'getThreadMessages',
        threadId
      });
      throw error;
    }
  }

  // Local Cache Management
  async cacheMessages(threadId: string, messages: Message[]): Promise<void> {
    const key = `messages_${threadId}`;
    localStorage.setItem(key, JSON.stringify(messages));
  }

  async getCachedMessages(threadId: string): Promise<Message[]> {
    const key = `messages_${threadId}`;
    const cached = localStorage.getItem(key);
    return cached ? JSON.parse(cached) : [];
  }

  async syncMessages(threadId: string): Promise<Message[]> {
    const localMessages = await this.getCachedMessages(threadId);
    
    try {
      const serverMessages = await this.getThreadMessages(threadId) as Message[];
      
      // Merge local and server messages
      const messageMap = new Map<string, Message>();
      
      // Add server messages first (they have priority)
      serverMessages.forEach(msg => {
        if (msg.id) {
          messageMap.set(msg.id, msg);
        }
      });
      
      // Add local messages that aren't on server
      localMessages.forEach(msg => {
        if (msg.id && !messageMap.has(msg.id)) {
          messageMap.set(msg.id, msg);
        }
      });
      
      const merged = Array.from(messageMap.values());
      await this.cacheMessages(threadId, merged);
      
      return merged;
    } catch (error) {
      // If sync fails, return local messages
      return localMessages;
    }
  }

  async getQueuedMessages(): Promise<QueuedMessage[]> {
    return [...this.queuedMessages];
  }

  async retryQueuedMessages(): Promise<{ successful: number; failed: number }> {
    let successful = 0;
    let failed = 0;
    const remainingQueued: QueuedMessage[] = [];
    const messagesToRetry = [...this.queuedMessages];

    for (const queued of messagesToRetry) {
      try {
        await this.saveMessage(queued.thread_id, queued.message);
        successful++;
      } catch (error) {
        failed++;
        remainingQueued.push(queued);
      }
    }

    this.queuedMessages = remainingQueued;

    return { successful, failed };
  }

  // Thread State Management
  async saveThreadState(state: MessageThreadState): Promise<void> {
    this.threadStates.set(state.thread_id, state);
    localStorage.setItem(`thread_state_${state.thread_id}`, JSON.stringify(state));
  }

  async getThreadState(threadId: string): Promise<MessageThreadState | null> {
    // Check memory first
    if (this.threadStates.has(threadId)) {
      return this.threadStates.get(threadId)!;
    }

    // Check localStorage
    const stored = localStorage.getItem(`thread_state_${threadId}`);
    if (stored) {
      const state = JSON.parse(stored);
      this.threadStates.set(threadId, state);
      return state;
    }

    return null;
  }

  async updateThreadMetadata(threadId: string, metadata: any): Promise<void> {
    try {
      const response = await authInterceptor.patch(`/api/threads/${threadId}/metadata`, metadata);
      
      if (!response.ok) {
        const errorData = await response.text();
        let errorMessage: string;
        try {
          const parsed = JSON.parse(errorData);
          errorMessage = parsed.detail || parsed.message || parsed.error || `Failed to update thread metadata: ${response.statusText}`;
        } catch {
          errorMessage = errorData || `Failed to update thread metadata: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }
    } catch (error) {
      logger.error('Failed to update thread metadata', error as Error, {
        component: 'MessageService',
        action: 'updateThreadMetadata',
        threadId
      });
      throw error;
    }
  }

  // Reset method for testing
  _reset(): void {
    this.queuedMessages = [];
    this.threadStates.clear();
  }
}

export const messageService = new MessageService();