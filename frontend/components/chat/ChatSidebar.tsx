"use client";

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, MessageSquare, Clock, ChevronRight, Search } from 'lucide-react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

interface Thread {
  id: string;
  object: 'thread';
  created_at: number;
  metadata: Record<string, any>;
  last_message?: string;
  message_count?: number;
  updated_at?: number;
}

export const ChatSidebar: React.FC = () => {
  const { 
    activeThreadId, 
    threads, 
    switchThread, 
    createThread,
    isProcessing 
  } = useUnifiedChatStore();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreatingThread, setIsCreatingThread] = useState(false);

  // Filter threads based on search
  const filteredThreads = Array.from(threads.values()).filter(thread => {
    if (!searchQuery) return true;
    return thread.last_message?.toLowerCase().includes(searchQuery.toLowerCase());
  });

  // Sort threads by last update
  const sortedThreads = filteredThreads.sort((a, b) => {
    const aTime = a.updated_at || a.created_at;
    const bTime = b.updated_at || b.created_at;
    return bTime - aTime;
  });

  const handleNewChat = async () => {
    setIsCreatingThread(true);
    try {
      const threadId = await createThread();
      await switchThread(threadId);
    } finally {
      setIsCreatingThread(false);
    }
  };

  const handleThreadClick = async (threadId: string) => {
    if (threadId === activeThreadId || isProcessing) return;
    await switchThread(threadId);
  };

  return (
    <div className="w-80 h-full bg-white/95 backdrop-blur-md border-r border-gray-200 flex flex-col">
      {/* Header with New Chat Button */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={handleNewChat}
          disabled={isCreatingThread || isProcessing}
          className={cn(
            "w-full flex items-center justify-center space-x-2 px-4 py-3",
            "bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg",
            "transition-all duration-200 transform hover:scale-[1.02]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "shadow-sm hover:shadow-md"
          )}
        >
          {isCreatingThread ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Plus className="w-5 h-5" />
            </motion.div>
          ) : (
            <Plus className="w-5 h-5" />
          )}
          <span className="font-medium">New Chat</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="p-4 border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-200"
          />
        </div>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="popLayout">
          {sortedThreads.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-20" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Start a new chat to begin</p>
            </div>
          ) : (
            sortedThreads.map((thread) => (
              <motion.div
                key={thread.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
              >
                <button
                  onClick={() => handleThreadClick(thread.id)}
                  disabled={isProcessing}
                  className={cn(
                    "w-full p-4 text-left hover:bg-gray-50 transition-colors duration-200",
                    "border-b border-gray-100 group relative",
                    activeThreadId === thread.id && "bg-emerald-50 hover:bg-emerald-50",
                    "disabled:opacity-50 disabled:cursor-not-allowed"
                  )}
                >
                  {/* Active Indicator */}
                  {activeThreadId === thread.id && (
                    <motion.div
                      layoutId="activeIndicator"
                      className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                    />
                  )}

                  <div className="flex items-start space-x-3 pl-2">
                    <MessageSquare className={cn(
                      "w-5 h-5 mt-0.5 flex-shrink-0",
                      activeThreadId === thread.id ? "text-emerald-600" : "text-gray-400"
                    )} />
                    
                    <div className="flex-1 min-w-0">
                      {/* Thread Title / Last Message */}
                      <p className={cn(
                        "text-sm font-medium truncate",
                        activeThreadId === thread.id ? "text-emerald-900" : "text-gray-900"
                      )}>
                        {thread.last_message || `Thread ${thread.id.slice(0, 8)}`}
                      </p>
                      
                      {/* Metadata */}
                      <div className="flex items-center space-x-3 mt-1">
                        <span className="text-xs text-gray-500 flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {formatDistanceToNow(thread.updated_at || thread.created_at, { addSuffix: true })}
                        </span>
                        {thread.message_count && thread.message_count > 0 && (
                          <span className="text-xs text-gray-500">
                            {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Chevron on Hover */}
                    <ChevronRight className={cn(
                      "w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
                      activeThreadId === thread.id && "opacity-100 text-emerald-600"
                    )} />
                  </div>

                  {/* Processing Indicator for Background Threads */}
                  {thread.metadata?.isProcessing && thread.id !== activeThreadId && (
                    <div className="absolute top-2 right-2">
                      <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                    </div>
                  )}
                </button>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Footer with Thread Count */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <p className="text-xs text-gray-500 text-center">
          {threads.size} conversation{threads.size !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};