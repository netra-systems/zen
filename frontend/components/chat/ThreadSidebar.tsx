"use client";

import React, { useEffect, useState } from 'react';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useThreadCreation } from '@/hooks/useThreadCreation';
import { ThreadErrorBoundary } from './ThreadErrorBoundary';
import { ThreadLoadingIndicator } from './ThreadLoadingIndicator';
import { useThreadSidebarActions } from './ThreadSidebarActions';
import {
  ThreadSidebarHeader,
  ThreadItem,
  ThreadEmptyState,
  ThreadAuthRequiredState
} from './ThreadSidebarComponents';
import { AnimatePresence } from 'framer-motion';

export const ThreadSidebar: React.FC = () => {
  const { threads, currentThreadId } = useThreadStore();
  const { isAuthenticated } = useAuthStore();
  const { state: switchingState } = useThreadSwitching();
  const { state: creationState } = useThreadCreation();
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  
  const {
    loadThreads,
    handleCreateThread,
    handleSelectThread,
    handleUpdateTitle,
    handleDeleteThread,
    formatDate,
    handleErrorBoundaryError,
    handleErrorBoundaryRetry
  } = useThreadSidebarActions();

  useEffect(() => {
    if (isAuthenticated) {
      loadThreads();
    }
  }, [isAuthenticated, loadThreads]);

  const handleTitleUpdate = async (threadId: string) => {
    await handleUpdateTitle(threadId, editingTitle, setEditingThreadId, setEditingTitle);
  };

  const handleEditStart = (thread: any) => {
    setEditingThreadId(thread.id);
    setEditingTitle(thread.title || 'Untitled Conversation');
  };

  const handleEditCancel = () => {
    setEditingThreadId(null);
  };

  const handleBoundaryRetry = (threadId?: string) => {
    handleErrorBoundaryRetry(threadId, loadThreads, handleSelectThread);
  };

  if (!isAuthenticated) {
    return <ThreadAuthRequiredState />;
  }

  return (
    <ThreadErrorBoundary
      onError={handleErrorBoundaryError}
      onRetry={handleBoundaryRetry}
    >
      <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
        <ThreadSidebarHeader
          onCreateThread={handleCreateThread}
          isCreating={creationState.isCreating}
          isLoading={switchingState.isLoading}
          isAuthenticated={isAuthenticated}
        />

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
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
              <ThreadItem
                key={thread.id}
                thread={thread}
                currentThreadId={currentThreadId}
                isLoading={switchingState.isLoading}
                loadingThreadId={switchingState.loadingThreadId}
                editingThreadId={editingThreadId}
                editingTitle={editingTitle}
                onSelect={() => handleSelectThread(thread.id)}
                onEdit={() => handleEditStart(thread)}
                onDelete={() => handleDeleteThread(thread.id)}
                onTitleChange={setEditingTitle}
                onSaveTitle={() => handleTitleUpdate(thread.id)}
                onCancelEdit={handleEditCancel}
                formatDate={formatDate}
              />
            ))}
          </AnimatePresence>

          {threads.length === 0 && <ThreadEmptyState />}
        </div>
      </div>
    </ThreadErrorBoundary>
  );
};