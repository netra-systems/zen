import { useThreadStore } from '@/store/threadStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useThreadCreation } from '@/hooks/useThreadCreation';
import { useAuth } from '@/hooks/useAuth';
import { defaultRecoveryManager } from '@/lib/thread-error-recovery';
import { createThreadErrorFromError } from './ThreadSidebarErrorHandling';
import { logger } from '@/utils/debug-logger';
import {
  executeThreadLoad,
  executeThreadCreation,
  executeThreadSelection,
  executeTitleUpdate,
  executeThreadDeletion,
  shouldSkipThreadSelection,
  shouldSkipTitleUpdate,
  calculateDateDifference,
  formatDateDisplay
} from '@/hooks/thread-sidebar-utils';

export interface ThreadSidebarActionsResult {
  loadThreads: () => Promise<void>;
  handleCreateThread: () => Promise<void>;
  handleSelectThread: (threadId: string) => Promise<void>;
  handleUpdateTitle: (threadId: string, editingTitle: string, setEditingThreadId: (id: string | null) => void, setEditingTitle: (title: string) => void) => Promise<void>;
  handleDeleteThread: (threadId: string) => Promise<void>;
  formatDate: (timestamp: number) => string;
  handleThreadError: (error: unknown, threadId: string) => Promise<void>;
  handleErrorBoundaryError: (error: Error, errorInfo: any, threadId?: string) => void;
  handleErrorBoundaryRetry: (threadId?: string, loadThreads?: () => Promise<void>, handleSelectThread?: (threadId: string) => Promise<void>) => void;
}

/**
 * Custom hook providing all thread sidebar actions
 */
export const useThreadSidebarActions = (): ThreadSidebarActionsResult => {
  const { 
    setThreads, 
    setCurrentThread,
    updateThread,
    deleteThread,
    setLoading,
    setError,
    currentThreadId
  } = useThreadStore();
  
  const { clearMessages } = useUnifiedChatStore();
  const { state: switchingState, switchToThread } = useThreadSwitching();
  const { state: creationState, createAndNavigate } = useThreadCreation();
  const { isAuthenticated } = useAuth();

  const loadThreads = async () => {
    await executeThreadLoad(setLoading, setThreads, setError, isAuthenticated);
  };

  const handleCreateThread = async () => {
    await executeThreadCreation(createAndNavigate, loadThreads, creationState, setError);
  };

  const handleSelectThread = async (threadId: string) => {
    if (shouldSkipThreadSelection(threadId, currentThreadId, switchingState.isLoading)) return;
    
    try {
      await executeThreadSelection(threadId, switchToThread, setCurrentThread, switchingState, setError);
    } catch (error) {
      await handleThreadError(error, threadId);
    }
  };

  const handleUpdateTitle = async (
    threadId: string, 
    editingTitle: string, 
    setEditingThreadId: (id: string | null) => void, 
    setEditingTitle: (title: string) => void
  ) => {
    if (shouldSkipTitleUpdate(editingTitle, setEditingThreadId)) return;

    await executeTitleUpdate(threadId, editingTitle, updateThread, setEditingThreadId, setEditingTitle, setError);
  };

  const handleDeleteThread = async (threadId: string) => {
    if (!confirm('Delete this conversation? This cannot be undone.')) return;
    
    await executeThreadDeletion(threadId, deleteThread, currentThreadId, clearMessages, setError);
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    const days = calculateDateDifference(timestamp);
    return formatDateDisplay(days, date);
  };

  const handleThreadError = async (error: unknown, threadId: string) => {
    const threadError = createThreadErrorFromError(threadId, error);
    const recoveryResult = await defaultRecoveryManager.recover(threadError);
    
    if (recoveryResult.shouldRetry && recoveryResult.success) {
      // Auto-retry if recovery suggests it
      setTimeout(() => handleSelectThread(threadId), recoveryResult.nextRetryDelay || 2000);
    }
  };

  const handleErrorBoundaryError = (error: Error, errorInfo: any, threadId?: string) => {
    logger.error('Thread error boundary caught error:', { error, errorInfo, threadId });
  };

  const handleErrorBoundaryRetry = (
    threadId?: string, 
    loadThreads?: () => Promise<void>, 
    handleSelectThread?: (threadId: string) => Promise<void>
  ) => {
    if (threadId && handleSelectThread) {
      handleSelectThread(threadId);
    } else if (loadThreads) {
      loadThreads();
    }
  };

  return {
    loadThreads,
    handleCreateThread,
    handleSelectThread,
    handleUpdateTitle,
    handleDeleteThread,
    formatDate,
    handleThreadError,
    handleErrorBoundaryError,
    handleErrorBoundaryRetry
  };
};