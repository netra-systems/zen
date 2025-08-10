import { apiClient } from '@/services/apiClient';

export interface Thread {
  id: string;
  object?: string;
  title?: string;
  created_at: number;
  updated_at?: number;
  metadata?: any;
  message_count: number;
}

export interface ThreadMessage {
  id: string;
  role: string;
  content: string;
  created_at: number;
  metadata?: any;
}

export interface ThreadMessagesResponse {
  thread_id: string;
  messages: ThreadMessage[];
  total: number;
  limit: number;
  offset: number;
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

  static async createThread(title?: string, metadata?: any): Promise<Thread> {
    const response = await apiClient.post<Thread>('/api/threads', {
      title,
      metadata
    });
    return response.data;
  }

  static async updateThread(threadId: string, title?: string, metadata?: any): Promise<Thread> {
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