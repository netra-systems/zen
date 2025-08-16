"use client";

import React, { useEffect, useState } from 'react';
import { useThreadStore } from '@/store/threadStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useThreadCreation } from '@/hooks/useThreadCreation';
import { ThreadErrorBoundary } from './ThreadErrorBoundary';
import { ThreadLoadingIndicator } from './ThreadLoadingIndicator';
import { defaultRecoveryManager } from '@/lib/thread-error-recovery';
import type { ThreadError, ThreadErrorCategory } from '@/types/thread-error-types';
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
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, 
  MessageSquare,
  Trash2,
  Pencil,
  X,
  Check,
  Loader2
} from 'lucide-react';

// Helper functions imported from thread-sidebar-utils module

export const ThreadSidebar: React.FC = () => {
  const { 
    threads, 
    currentThreadId, 
    setThreads, 
    setCurrentThread,
    addThread,
    updateThread,
    deleteThread,
    setLoading,
    setError
  } = useThreadStore();
  
  const { clearMessages } = useUnifiedChatStore();
  const { isAuthenticated } = useAuthStore();
  const { state: switchingState, switchToThread } = useThreadSwitching();
  const { state: creationState, createAndNavigate } = useThreadCreation();
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  useEffect(() => {
    // Only load threads if user is authenticated
    if (isAuthenticated) {
      loadThreads();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const loadThreads = async () => {
    await executeThreadLoad(setLoading, setThreads, setError);
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

  const handleUpdateTitle = async (threadId: string) => {
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
    console.error('Thread error boundary caught error:', { error, errorInfo, threadId });
  };

  const handleErrorBoundaryRetry = (threadId?: string) => {
    if (threadId) {
      handleSelectThread(threadId);
    } else {
      loadThreads();
    }
  };

  // Show authentication message if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p className="text-gray-600 mb-2">Please sign in to view conversations</p>
            <p className="text-sm text-gray-500">Sign in to access your chat history</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ThreadErrorBoundary
      onError={handleErrorBoundaryError}
      onRetry={handleErrorBoundaryRetry}
    >
      <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={handleCreateThread}
            disabled={creationState.isCreating || switchingState.isLoading || !isAuthenticated}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 glass-button-primary rounded-lg transition-all disabled:glass-disabled"
          >
            {creationState.isCreating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Plus className="w-5 h-5" />
            )}
            <span>New Conversation</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {/* Loading indicator for current operation */}
          {switchingState.isLoading && (
            <ThreadLoadingIndicator
              state={switchingState.error ? 'error' : 'loading'}
              threadId={switchingState.loadingThreadId || undefined}
              error={switchingState.error}
              retryCount={switchingState.retryCount}
              onRetry={() => {
                if (switchingState.loadingThreadId) {
                  handleSelectThread(switchingState.loadingThreadId);
                }
              }}
              showDetails={true}
            />
          )}
          
          <AnimatePresence>
            {threads.map((thread) => (
              <motion.div
                key={thread.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className={`
                  group relative p-3 rounded-lg cursor-pointer transition-all
                  ${currentThreadId === thread.id 
                    ? 'bg-white shadow-md border border-blue-200' 
                    : 'hover:bg-white hover:shadow-sm'
                  }
                  ${switchingState.loadingThreadId === thread.id ? 'opacity-75' : ''}
                  ${switchingState.isLoading && thread.id !== switchingState.loadingThreadId ? 'pointer-events-none opacity-50' : ''}
                `}
                onClick={() => handleSelectThread(thread.id)}
              >
                <div className="flex items-start gap-3">
                  {switchingState.loadingThreadId === thread.id ? (
                    <Loader2 className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0 animate-spin" />
                  ) : (
                    <MessageSquare className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    {editingThreadId === thread.id ? (
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleUpdateTitle(thread.id);
                            if (e.key === 'Escape') setEditingThreadId(null);
                          }}
                          className="flex-1 px-2 py-1 text-sm border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                          autoFocus
                        />
                        <button
                          onClick={() => handleUpdateTitle(thread.id)}
                          className="p-1 text-green-600 hover:bg-green-50 rounded"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingThreadId(null)}
                          className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {thread.title || 'Untitled Conversation'}
                        </h3>
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-xs text-gray-500">
                            {formatDate(thread.created_at)}
                          </span>
                          {thread.message_count && thread.message_count > 0 && (
                            <span className="text-xs text-gray-400">
                              · {thread.message_count} messages
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {editingThreadId !== thread.id && (
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingThreadId(thread.id);
                          setEditingTitle(thread.title || 'Untitled Conversation');
                        }}
                        className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteThread(thread.id);
                        }}
                        className="p-1 text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {threads.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Start a new conversation to begin</p>
            </div>
          )}
        </div>
      </div>
    </ThreadErrorBoundary>
  );
};

/**
 * Creates thread error from generic error
 */
const createThreadErrorFromError = (threadId: string, error: unknown): ThreadError => {
  const message = error instanceof Error ? error.message : String(error);
  
  return {
    id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    threadId,
    message,
    category: categorizeErrorMessage(message),
    severity: 'medium',
    timestamp: Date.now(),
    retryable: isErrorRetryable(message)
  };
};

/**
 * Categorizes error message
 */
const categorizeErrorMessage = (message: string): ThreadErrorCategory => {
  const lowerMessage = message.toLowerCase();
  
  if (lowerMessage.includes('timeout')) return 'timeout';
  if (lowerMessage.includes('network') || lowerMessage.includes('fetch')) return 'network';
  if (lowerMessage.includes('abort')) return 'abort';
  
  return 'unknown';
};

/**
 * Checks if error is retryable
 */
const isErrorRetryable = (message: string): boolean => {
  const lowerMessage = message.toLowerCase();
  return !lowerMessage.includes('abort') && !lowerMessage.includes('permission');
};