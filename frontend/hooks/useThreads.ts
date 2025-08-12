import { useState, useEffect, useCallback } from 'react';
import { threadService } from '@/services/threadService';

export interface Thread {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messages: number;
}

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThreads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await threadService.getThreads();
      setThreads(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch threads');
    } finally {
      setLoading(false);
    }
  }, []);

  const createThread = useCallback(async (title: string) => {
    setError(null);
    try {
      const newThread = await threadService.createThread(title);
      setThreads(prev => [newThread, ...prev]);
      return newThread;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create thread');
      throw err;
    }
  }, []);

  const deleteThread = useCallback(async (threadId: string) => {
    setError(null);
    try {
      await threadService.deleteThread(threadId);
      setThreads(prev => prev.filter(t => t.id !== threadId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete thread');
      throw err;
    }
  }, []);

  const renameThread = useCallback(async (threadId: string, newTitle: string) => {
    setError(null);
    try {
      const updated = await threadService.renameThread(threadId, newTitle);
      setThreads(prev => prev.map(t => t.id === threadId ? { ...t, title: newTitle } : t));
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename thread');
      throw err;
    }
  }, []);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  return {
    threads,
    loading,
    error,
    fetchThreads,
    createThread,
    deleteThread,
    renameThread
  };
}