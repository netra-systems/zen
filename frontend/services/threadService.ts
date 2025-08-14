import { apiClient } from '@/services/apiClientWrapper';

export interface ThreadMetadata {
  userId?: string;
  createdAt?: string;
  lastActivity?: string;
  messageCount?: number;
  tags?: string[];
  priority?: 'low' | 'medium' | 'high';
  archived?: boolean;
  [key: string]: string | number | boolean | string[] | undefined;
}

export interface MessageMetadata {
  references?: string[];
  attachments?: Array<{
    id: string;
    filename: string;
    mimeType: string;
    size: number;
  }>;
  editedAt?: string;
  [key: string]: unknown;
}

export interface Thread {
  id: string;
  object?: string;
  title?: string;
  created_at: number;
  updated_at?: number;
  metadata?: ThreadMetadata;
  message_count: number;
}

export interface ThreadMessage {
  id: string;
  role: string;
  content: string;
  created_at: number;
  metadata?: MessageMetadata;
}

export interface ThreadMessagesResponse {
  thread_id: string;
  messages: ThreadMessage[];
  total: number;
  limit: number;
  offset: number;
  metadata?: ThreadMetadata;
}

export class ThreadService {
  static async listThreads(limit = 20, offset = 0): Promise<Thread[]> {
    const response = await apiClient.get<Thread[]>('/api/threads', {
      params: { limit, offset }
    });
    return response.data;
  }

  static async getThread(threadId: string): Promise<Thread> {
    const response = await apiClient.get<Thread>(`/api/threads/${threadId}`);
    return response.data;
  }

  static async createThread(title?: string, metadata?: ThreadMetadata): Promise<Thread> {
    const response = await apiClient.post<Thread>('/api/threads', {
      title,
      metadata
    });
    return response.data;
  }

  static async updateThread(threadId: string, title?: string, metadata?: ThreadMetadata): Promise<Thread> {
    const response = await apiClient.put<Thread>(`/api/threads/${threadId}`, {
      title,
      metadata
    });
    return response.data;
  }

  static async deleteThread(threadId: string): Promise<void> {
    await apiClient.delete(`/api/threads/${threadId}`);
  }

  static async getThreadMessages(
    threadId: string, 
    limit = 50, 
    offset = 0
  ): Promise<ThreadMessagesResponse> {
    const response = await apiClient.get<ThreadMessagesResponse>(
      `/api/threads/${threadId}/messages`,
      { params: { limit, offset } }
    );
    return response.data;
  }
}