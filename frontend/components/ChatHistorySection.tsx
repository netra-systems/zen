"use client";

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useThreadStore } from '@/store/threadStore';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { motion, AnimatePresence } from 'framer-motion';
import { logger } from '@/lib/logger';
import { 
  Plus, 
  MessageSquare,
  Trash2,
  Pencil,
  X,
  Check
} from 'lucide-react';

export const ChatHistorySection: React.FC = () => {
  const router = useRouter();
  const pathname = usePathname();
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
  
  const { clearMessages, loadMessages } = useChatStore();
  const { isAuthenticated } = useAuthStore();
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      loadThreads();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const loadThreads = async () => {
    if (!isAuthenticated) {
      setThreads([]);
      return;
    }
    try {
      setLoading(true);
      const fetchedThreads = await ThreadService.listThreads();
      setThreads(fetchedThreads);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation history';
      logger.error('Failed to load threads:', errorMessage);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateThread = async () => {
    try {
      setIsCreatingNew(true);
      const newThread = await ThreadService.createThread('New Conversation');
      addThread(newThread);
      await handleSelectThread(newThread.id);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create new conversation';
      logger.error('Failed to create thread:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsCreatingNew(false);
    }
  };

  const handleSelectThread = async (threadId: string) => {
    if (threadId === currentThreadId) return;
    
    try {
      setCurrentThread(threadId);
      clearMessages();
      
      // Navigate to chat page if not already there
      if (!pathname?.startsWith('/chat')) {
        router.push('/chat');
      }
      
      // Load messages for the selected thread
      const response = await ThreadService.getThreadMessages(threadId);
      if (response.messages.length > 0) {
        loadMessages(response.messages);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation';
      logger.error('Failed to load thread messages:', errorMessage);
      setError(errorMessage);
    }
  };

  const handleUpdateTitle = async (threadId: string) => {
    if (!editingTitle.trim()) {
      setEditingThreadId(null);
      return;
    }

    try {
      const updated = await ThreadService.updateThread(threadId, editingTitle);
      updateThread(threadId, { title: updated.title });
      setEditingThreadId(null);
      setEditingTitle('');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update thread title';
      logger.error('Failed to update thread title:', errorMessage);
      setError(errorMessage);
    }
  };

  const handleDeleteThread = async (threadId: string) => {
    if (!confirm('Delete this conversation? This cannot be undone.')) return;
    
    try {
      await ThreadService.deleteThread(threadId);
      deleteThread(threadId);
      
      if (currentThreadId === threadId) {
        clearMessages();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete conversation';
      logger.error('Failed to delete thread:', errorMessage);
      setError(errorMessage);
    }
  };

  const formatDate = (timestamp: string | number | null | undefined) => {
    if (!timestamp) return 'Unknown date';
    
    // Unix timestamps from backend are in seconds, need to convert to milliseconds
    const date = typeof timestamp === 'string' 
      ? new Date(timestamp) 
      : new Date(timestamp * 1000);
    if (isNaN(date.getTime())) return 'Unknown date';
    
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  // Constants for conversation limiting
  const MAX_VISIBLE_CONVERSATIONS = 4;
  const visibleThreads = threads.slice(0, MAX_VISIBLE_CONVERSATIONS);
  const hasMoreConversations = threads.length > MAX_VISIBLE_CONVERSATIONS;
  const hiddenCount = threads.length - MAX_VISIBLE_CONVERSATIONS;

  if (!isAuthenticated) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="text-center">
          <MessageSquare className="w-10 h-10 mx-auto mb-3 text-gray-400" />
          <p className="text-sm text-gray-600">Sign in to view chats</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pt-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Chat History
        </h3>
        <button
          onClick={handleCreateThread}
          disabled={isCreatingNew || !isAuthenticated}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1" data-testid="chat-history-list">
        <AnimatePresence>
          {visibleThreads.map((thread) => (
            <motion.div
              key={thread.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className={`
                group relative px-3 py-2 rounded-lg cursor-pointer transition-all text-sm
                ${currentThreadId === thread.id 
                  ? 'bg-accent text-accent-foreground' 
                  : 'hover:bg-accent/50'
                }
              `}
              onClick={() => handleSelectThread(thread.id)}
              data-testid={`chat-history-item-${thread.id}`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                
                <div className="flex-1 min-w-0">
                  {editingThreadId === thread.id ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleUpdateTitle(thread.id);
                          if (e.key === 'Escape') setEditingThreadId(null);
                        }}
                        className="flex-1 px-2 py-0.5 text-xs border rounded focus:outline-none focus:ring-1 focus:ring-primary"
                        autoFocus
                      />
                      <button
                        onClick={() => handleUpdateTitle(thread.id)}
                        className="p-0.5 text-green-600 hover:bg-green-50 rounded"
                      >
                        <Check className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setEditingThreadId(null)}
                        className="p-0.5 text-gray-600 hover:bg-gray-100 rounded"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <h3 className="font-medium truncate">
                        {thread.title || 'Untitled'}
                      </h3>
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className="text-xs text-muted-foreground">
                          {formatDate(thread.created_at)}
                        </span>
                      </div>
                    </>
                  )}
                </div>

                {editingThreadId !== thread.id && (
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingThreadId(thread.id);
                        setEditingTitle(thread.title || 'Untitled');
                      }}
                      className="p-0.5 text-gray-600 hover:bg-gray-100 rounded"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteThread(thread.id);
                      }}
                      className="p-0.5 text-red-600 hover:bg-red-50 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Overflow indicator for additional conversations */}
        {hasMoreConversations && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="px-3 py-2 text-center border-t border-gray-100 mt-2"
            data-testid="conversation-overflow-indicator"
          >
            <p className="text-xs text-muted-foreground">
              +{hiddenCount} more conversation{hiddenCount > 1 ? 's' : ''}
            </p>
            <button 
              className="text-xs text-primary hover:text-primary/80 underline mt-1"
              onClick={() => {/* TODO: Implement view all conversations */}}
            >
              View all
            </button>
          </motion.div>
        )}

        {threads.length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <MessageSquare className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            <p className="text-xs">No conversations yet</p>
          </div>
        )}
      </div>
    </div>
  );
};