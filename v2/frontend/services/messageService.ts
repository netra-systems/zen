import { Message } from '@/types/chat';

interface Thread {
  id: string;
  created_at: number;
  metadata_?: any;
}

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

interface ThreadState {
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
  private threadStates: Map<string, ThreadState> = new Map();

  private getAuthHeader(): string {
    const token = localStorage.getItem('auth_token') || '';
    return `Bearer ${token}`;
  }

  // Thread Management
  async createThread(userId: string): Promise<Thread> {
    const response = await fetch('/api/threads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': this.getAuthHeader(),
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create thread: ${response.statusText}`);
    }

    return response.json();
  }

  async getThreads(userId: string): Promise<Thread[]> {
    const response = await fetch(`/api/threads?user_id=${userId}`, {
      method: 'GET',
      headers: {
        'Authorization': this.getAuthHeader(),
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch threads: ${response.statusText}`);
    }

    return response.json();
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

    const response = await fetch(`/api/threads/${threadId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': this.getAuthHeader(),
      },
      body: JSON.stringify(message),
    });

    if (!response.ok) {
      throw new Error(`Failed to save message: ${response.statusText}`);
    }

    return response.json();
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

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': this.getAuthHeader(),
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch messages: ${response.statusText}`);
    }

    const data = await response.json();
    
    // Handle both paginated and non-paginated responses
    if (options.limit && data.messages) {
      return data;
    }
    
    return data;
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
      serverMessages.forEach(msg => messageMap.set(msg.id, msg));
      
      // Add local messages that aren't on server
      localMessages.forEach(msg => {
        if (!messageMap.has(msg.id)) {
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

    for (const queued of this.queuedMessages) {
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
  async saveThreadState(state: ThreadState): Promise<void> {
    this.threadStates.set(state.thread_id, state);
    localStorage.setItem(`thread_state_${state.thread_id}`, JSON.stringify(state));
  }

  async getThreadState(threadId: string): Promise<ThreadState | null> {
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
    const response = await fetch(`/api/threads/${threadId}/metadata`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': this.getAuthHeader(),
      },
      body: JSON.stringify(metadata),
    });

    if (!response.ok) {
      throw new Error(`Failed to update thread metadata: ${response.statusText}`);
    }
  }
}

export const messageService = new MessageService();