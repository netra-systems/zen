"use client";

import React, { useEffect, useState } from 'react';
import { useThreadStore } from '@/store/threadStore';
import { useChatStore } from '@/store/chat';
import { useAuthStore } from '@/store/authStore';
import { ThreadService } from '@/services/threadService';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, 
  MessageSquare,
  Trash2,
  Pencil,
  X,
  Check
} from 'lucide-react';

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
  
  const { clearMessages, loadMessages } = useChatStore();
  const { isAuthenticated } = useAuthStore();
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  useEffect(() => {
    // Only load threads if user is authenticated
    if (isAuthenticated) {
      loadThreads();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const loadThreads = async () => {
    try {
      setLoading(true);
      const fetchedThreads = await ThreadService.listThreads();
      setThreads(fetchedThreads);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation history';
      console.error('Failed to load threads:', errorMessage);
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
      console.error('Failed to create thread:', errorMessage);
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
      
      // Load messages for the selected thread
      const response = await ThreadService.getThreadMessages(threadId);
      if (response.messages.length > 0) {
        loadMessages(response.messages);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load conversation';
      console.error('Failed to load thread messages:', errorMessage);
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
      console.error('Failed to update thread title:', errorMessage);
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
      console.error('Failed to delete thread:', errorMessage);
      setError(errorMessage);
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
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
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={handleCreateThread}
          disabled={isCreatingNew || !isAuthenticated}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          <Plus className="w-5 h-5" />
          <span>New Conversation</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
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
              `}
              onClick={() => handleSelectThread(thread.id)}
            >
              <div className="flex items-start gap-3">
                <MessageSquare className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
                
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
  );
};