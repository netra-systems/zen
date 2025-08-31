/**
 * Thread Sidebar Utilities
 * 
 * Extracted helper functions from ThreadSidebar.tsx to maintain 450-line file limit
 * Provides specialized operations for thread management
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed utility functions
 */

import { logger } from '@/lib/logger';
import { ThreadService } from '@/services/threadService';
import { useAuthStore } from '@/store/authStore';

// ============================================
// Error Handling Functions (8 lines max each)
// ============================================

export const handleLoadThreadsError = (error: unknown, setError: (error: string) => void): void => {
  const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation history';
  logger.error('Failed to load threads:', errorMessage);
  setError(errorMessage);
};

export const handleCreateThreadError = (
  creationState: any,
  setError: (error: string) => void
): void => {
  const errorMessage = creationState.error || 'Failed to create new conversation';
  logger.error('Failed to create thread:', errorMessage);
  setError(errorMessage);
};

export const handleSelectThreadError = (
  switchingState: any,
  setError: (error: string) => void
): void => {
  const errorMessage = switchingState.error || 'Failed to load conversation';
  logger.error('Failed to load thread messages:', errorMessage);
  setError(errorMessage);
};

export const handleUpdateTitleError = (
  error: unknown,
  setError: (error: string) => void
): void => {
  const errorMessage = error instanceof Error ? error.message : 'Failed to update thread title';
  logger.error('Failed to update thread title:', errorMessage);
  setError(errorMessage);
};

export const handleDeleteThreadError = (
  error: unknown,
  setError: (error: string) => void
): void => {
  const errorMessage = error instanceof Error ? error.message : 'Failed to delete conversation';
  logger.error('Failed to delete thread:', errorMessage);
  setError(errorMessage);
};

// ============================================
// Main Operation Functions (8 lines max each)
// ============================================

export const executeThreadLoad = async (
  setLoading: (loading: boolean) => void,
  setThreads: (threads: any[]) => void,
  setError: (error: string) => void,
  isAuthenticated: boolean
): Promise<void> => {
  if (!isAuthenticated) {
    setThreads([]);
    return;
  }
  try {
    setLoading(true);
    const fetchedThreads = await ThreadService.listThreads();
    setThreads(fetchedThreads);
  } catch (error) {
    handleLoadThreadsError(error, setError);
  } finally {
    setLoading(false);
  }
};

export const executeThreadCreation = async (
  createAndNavigate: any,
  loadThreads: () => Promise<void>,
  creationState: any,
  setError: (error: string) => void
): Promise<void> => {
  const success = await createAndNavigate({
    title: 'New Conversation',
    navigateImmediately: true
  });
  
  if (success) {
    await loadThreads();
  } else {
    handleCreateThreadError(creationState, setError);
  }
};

export const executeThreadSelection = async (
  threadId: string,
  switchToThread: any,
  setCurrentThread: (id: string) => void,
  switchingState: any,
  setError: (error: string) => void
): Promise<void> => {
  const success = await switchToThread(threadId, {
    clearMessages: true,
    showLoadingIndicator: true
  });
  
  if (success) {
    setCurrentThread(threadId);
  } else {
    handleSelectThreadError(switchingState, setError);
  }
};

export const executeTitleUpdate = async (
  threadId: string,
  editingTitle: string,
  updateThread: any,
  setEditingThreadId: (id: string | null) => void,
  setEditingTitle: (title: string) => void,
  setError: (error: string) => void
): Promise<void> => {
  try {
    const updated = await ThreadService.updateThread(threadId, editingTitle);
    updateThread(threadId, { title: updated.title });
    setEditingThreadId(null);
    setEditingTitle('');
  } catch (error) {
    handleUpdateTitleError(error, setError);
  }
};

export const executeThreadDeletion = async (
  threadId: string,
  deleteThread: (id: string) => void,
  currentThreadId: string | null,
  clearMessages: () => void,
  setError: (error: string) => void
): Promise<void> => {
  try {
    await ThreadService.deleteThread(threadId);
    deleteThread(threadId);
    
    if (currentThreadId === threadId) {
      clearMessages();
    }
  } catch (error) {
    handleDeleteThreadError(error, setError);
  }
};

// ============================================
// Validation Functions (8 lines max each)  
// ============================================

export const shouldSkipThreadSelection = (
  threadId: string,
  currentThreadId: string | null,
  isLoading: boolean
): boolean => {
  return threadId === currentThreadId || isLoading;
};

export const shouldSkipTitleUpdate = (
  editingTitle: string,
  setEditingThreadId: (id: string | null) => void
): boolean => {
  if (!editingTitle.trim()) {
    setEditingThreadId(null);
    return true;
  }
  return false;
};

// ============================================
// Date Formatting Functions (8 lines max each)
// ============================================

export const calculateDateDifference = (timestamp: number): number => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
};

export const formatDateDisplay = (days: number, date: Date): string => {
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString();
};