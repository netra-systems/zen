"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, MessageSquare, Clock, ChevronLeft, ChevronRight, Search, Shield, Database, Sparkles, Users, Filter } from 'lucide-react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { ThreadService, Thread } from '@/services/threadService';

export const ChatSidebar: React.FC = () => {
  const { 
    isProcessing,
    activeThreadId,
    setActiveThread,
    clearMessages 
  } = useUnifiedChatStore();
  
  const { isDeveloperOrHigher } = useAuthStore();
  const isAdmin = isDeveloperOrHigher();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [showAllThreads, setShowAllThreads] = useState(false);
  const [filterType, setFilterType] = useState<'all' | 'corpus' | 'synthetic' | 'config' | 'users'>('all');
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const threadsPerPage = 50;

  // Load threads on mount and when filters change
  useEffect(() => {
    loadThreads();
  }, [showAllThreads, filterType]);

  const loadThreads = async () => {
    try {
      const fetchedThreads = await ThreadService.listThreads();
      setThreads(fetchedThreads);
    } catch (error) {
      console.error('Failed to load threads:', error);
    }
  };

  // Filter threads based on search
  const filteredThreads = threads.filter(thread => {
    if (!searchQuery) return true;
    const title = thread.metadata?.title || thread.title || `Chat ${thread.created_at}`;
    const lastMessage = thread.metadata?.last_message as string | undefined;
    return title.toLowerCase().includes(searchQuery.toLowerCase()) ||
           lastMessage?.toLowerCase().includes(searchQuery.toLowerCase());
  });

  // Sort threads by last update
  const sortedThreads = filteredThreads.sort((a, b) => {
    const aTime = a.updated_at || a.created_at;
    const bTime = b.updated_at || b.created_at;
    return bTime - aTime;
  });

  // Paginate threads
  const totalPages = Math.ceil(sortedThreads.length / threadsPerPage);
  const paginatedThreads = sortedThreads.slice(
    (currentPage - 1) * threadsPerPage,
    currentPage * threadsPerPage
  );

  const handleNewChat = async () => {
    setIsCreatingThread(true);
    try {
      const newThread = await ThreadService.createThread();
      
      // Set as active thread
      setActiveThread?.(newThread.id);
      clearMessages?.();
      
      // Reload threads list
      await loadThreads();
      
      // Auto-rename after first message (will be triggered by message send)
    } catch (error) {
      console.error('Failed to create thread:', error);
    } finally {
      setIsCreatingThread(false);
    }
  };

  const handleThreadClick = async (threadId: string) => {
    if (threadId === activeThreadId || isProcessing) return;
    
    try {
      // Clear current messages to ensure isolation
      clearMessages?.();
      
      // Disconnect from current WebSocket if needed
      const disconnectEvent = new CustomEvent('disconnectWebSocket', { 
        detail: { threadId: activeThreadId } 
      });
      window.dispatchEvent(disconnectEvent);
      
      // Switch to new thread
      setActiveThread?.(threadId);
      
      // Load thread messages
      const response = await ThreadService.getThreadMessages(threadId);
      
      // Emit thread loaded event
      const loadedEvent = new CustomEvent('threadLoaded', { 
        detail: { 
          threadId,
          messages: response.messages,
          metadata: response.metadata 
        } 
      });
      window.dispatchEvent(loadedEvent);
      
      // Connect to new thread WebSocket
      const connectEvent = new CustomEvent('connectWebSocket', { 
        detail: { threadId } 
      });
      window.dispatchEvent(connectEvent);
      
      console.log('Switched to thread:', threadId, 'with', response.messages.length, 'messages');
    } catch (error) {
      console.error('Failed to switch thread:', error);
    }
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

      {/* Admin Toggle for All Threads */}
      {isAdmin && (
        <div className="px-4 pt-2 pb-0">
          <div className="flex items-center justify-between p-2 bg-purple-50 rounded-lg border border-purple-200">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-900">Admin View</span>
            </div>
            <button
              onClick={() => setShowAllThreads(!showAllThreads)}
              className={cn(
                "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                showAllThreads 
                  ? "bg-purple-600 text-white" 
                  : "bg-white text-purple-600 border border-purple-300"
              )}
            >
              {showAllThreads ? 'All System Chats' : 'My Chats'}
            </button>
          </div>
          
          {/* Admin Filter Buttons */}
          {showAllThreads && (
            <div className="flex flex-wrap gap-1 mt-2">
              {[
                { key: 'all', icon: Filter, label: 'All' },
                { key: 'corpus', icon: Database, label: 'Corpus' },
                { key: 'synthetic', icon: Sparkles, label: 'Synthetic' },
                { key: 'users', icon: Users, label: 'Users' },
              ].map(({ key, icon: Icon, label }) => (
                <button
                  key={key}
                  onClick={() => setFilterType(key as 'all' | 'corpus' | 'synthetic' | 'config' | 'users')}
                  className={cn(
                    "flex items-center space-x-1 px-2 py-1 text-xs rounded-md transition-colors",
                    filterType === key
                      ? "bg-purple-100 text-purple-700 border border-purple-300"
                      : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
                  )}
                >
                  <Icon className="w-3 h-3" />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Search Bar */}
      <div className="p-4 border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={showAllThreads ? "Search all system chats..." : "Search conversations..."}
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
            paginatedThreads.map((thread) => (
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
                    {/* Icon based on thread type */}
                    {thread.metadata?.admin_type === 'corpus' ? (
                      <Database className={cn(
                        "w-5 h-5 mt-0.5 flex-shrink-0",
                        activeThreadId === thread.id ? "text-purple-600" : "text-purple-400"
                      )} />
                    ) : thread.metadata?.admin_type === 'synthetic' ? (
                      <Sparkles className={cn(
                        "w-5 h-5 mt-0.5 flex-shrink-0",
                        activeThreadId === thread.id ? "text-purple-600" : "text-purple-400"
                      )} />
                    ) : thread.metadata?.admin_type === 'users' ? (
                      <Users className={cn(
                        "w-5 h-5 mt-0.5 flex-shrink-0",
                        activeThreadId === thread.id ? "text-purple-600" : "text-purple-400"
                      )} />
                    ) : (
                      <MessageSquare className={cn(
                        "w-5 h-5 mt-0.5 flex-shrink-0",
                        activeThreadId === thread.id ? "text-emerald-600" : "text-gray-400"
                      )} />
                    )}
                    
                    <div className="flex-1 min-w-0">
                      {/* Thread Title / Last Message */}
                      <p className={cn(
                        "text-sm font-medium truncate",
                        activeThreadId === thread.id ? "text-emerald-900" : "text-gray-900"
                      )}>
                        {thread.metadata?.title || thread.title || thread.metadata?.last_message || `Chat ${new Date(thread.created_at * 1000).toLocaleDateString()}`}
                      </p>
                      
                      {/* Show user email for admin view */}
                      {showAllThreads && thread.metadata?.user_email && (
                        <p className="text-xs text-purple-600 truncate mt-0.5">
                          {thread.metadata?.user_email as string}
                        </p>
                      )}
                      
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

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="p-3 border-t border-gray-200 bg-white flex items-center justify-between">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          
          <span className="text-xs text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Footer with Thread Count and Quick Actions */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <p className="text-xs text-gray-500 text-center mb-2">
          {threads.length} conversation{threads.length !== 1 ? 's' : ''}
          {sortedThreads.length > threadsPerPage && ` (showing ${paginatedThreads.length})`}
        </p>
        
        {/* Admin Quick Actions */}
        {isAdmin && (
          <div className="flex flex-col space-y-1 mt-2">
            <button className="flex items-center justify-center space-x-2 p-2 text-xs bg-purple-100 text-purple-700 rounded-md hover:bg-purple-200 transition-colors">
              <Database className="w-3 h-3" />
              <span>Quick Create Corpus</span>
            </button>
            <button className="flex items-center justify-center space-x-2 p-2 text-xs bg-purple-100 text-purple-700 rounded-md hover:bg-purple-200 transition-colors">
              <Sparkles className="w-3 h-3" />
              <span>Generate Test Data</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};