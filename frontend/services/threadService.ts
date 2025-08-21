import { apiClient } from '@/services/apiClientWrapper';
import { Thread, ThreadMetadata, createThreadWithTitle } from '@/types/registry';
import type { MessageMetadata } from '@/types/registry';

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
    if (!response.data || !Array.isArray(response.data)) {
      throw new Error('Invalid response format from server');
    }
    return response.data;
  }

  static async getThread(threadId: string): Promise<Thread> {
    const response = await apiClient.get<Thread>(`/api/threads/${threadId}`);
    return response.data;
  }

  static async createThread(title?: string, metadata?: ThreadMetadata): Promise<Thread> {
    const response = await apiClient.post<Thread>('/api/threads', {
      title: title,
      metadata
    });
    return response.data;
  }

  static async updateThread(threadId: string, title?: string, metadata?: ThreadMetadata): Promise<Thread> {
    const response = await apiClient.put<Thread>(`/api/threads/${threadId}`, {
      title: title,
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

export const threadService = ThreadService;