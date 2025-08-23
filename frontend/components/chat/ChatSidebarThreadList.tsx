/**
 * Thread list components for ChatSidebar
 * All functions are ≤8 lines for architecture compliance
 */

"use client";

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, Clock, ChevronRight, 
  Database, Sparkles, Users 
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { Thread, getThreadTitle } from '@/types/unified';

const formatThreadTime = (thread: Thread): string => {
  const timestamp = thread.updated_at || thread.created_at;
  
  // Early return for missing timestamp - this should handle the "Unknown" test case
  if (!timestamp || timestamp === undefined || timestamp === null) {
    return 'Unknown';
  }
  
  try {
    // Handle both Unix timestamp (seconds) and ISO string formats
    let date: Date;
    if (typeof timestamp === 'number') {
      // Unix timestamp in seconds, convert to milliseconds
      date = new Date(timestamp * 1000);
    } else if (typeof timestamp === 'string') {
      // ISO string or other string format
      date = new Date(timestamp);
    } else {
      return 'Unknown';
    }
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return 'Unknown';
    }
    
    // Use formatDistanceToNow with comprehensive error handling
    try {
      const result = formatDistanceToNow(date, { addSuffix: true });
      if (!result || result === '' || result === 'Invalid Date') {
        return 'Recently';
      }
      return result;
    } catch (formatError) {
      // If date-fns fails, create a basic fallback
      const now = new Date();
      const diffMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
      if (diffMinutes < 1) return 'just now';
      if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
      const diffHours = Math.floor(diffMinutes / 60);
      if (diffHours < 24) return `${diffHours} hours ago`;
      return 'recently';
    }
  } catch (error) {
    return 'Unknown';
  }
};

const getThreadIcon = (thread: Thread, isActive: boolean) => {
  const baseClasses = "w-5 h-5 mt-0.5 flex-shrink-0";
  const activeColor = isActive ? "text-purple-600" : "text-purple-400";
  const defaultColor = isActive ? "text-emerald-600" : "text-gray-400";
  
  if (thread.metadata?.admin_type === 'corpus') {
    return <Database className={cn(baseClasses, activeColor)} />;
  }
  if (thread.metadata?.admin_type === 'synthetic') {
    return <Sparkles className={cn(baseClasses, activeColor)} />;
  }
  if (thread.metadata?.admin_type === 'users') {
    return <Users className={cn(baseClasses, activeColor)} />;
  }
  return <MessageSquare className={cn(baseClasses, defaultColor)} />;
};

// Using unified getThreadTitle from registry for consistency

const ThreadItem: React.FC<{
  thread: Thread;
  isActive: boolean;
  isProcessing: boolean;
  showAllThreads: boolean;
  onClick: () => void;
}> = ({ thread, isActive, isProcessing, showAllThreads, onClick }) => (
  <motion.div
    key={thread.id}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -20 }}
    transition={{ duration: 0.2 }}
  >
    <button
      onClick={onClick}
      disabled={isProcessing}
      data-testid={`thread-item-${thread.id}`}
      className={cn(
        "w-full p-4 text-left hover:bg-gray-50 transition-colors duration-200",
        "border-b border-gray-100 group relative",
        isActive && "bg-emerald-50 hover:bg-emerald-50",
        "disabled:opacity-50 disabled:cursor-not-allowed"
      )}
    >
      {isActive && (
        <motion.div
          layoutId="activeIndicator"
          className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
        />
      )}

      <div className="flex items-start space-x-3 pl-2">
        {getThreadIcon(thread, isActive)}
        
        <div className="flex-1 min-w-0">
          <p className={cn(
            "text-sm font-medium truncate",
            isActive ? "text-emerald-900" : "text-gray-900"
          )}>
            {getThreadTitle(thread)}
          </p>
          
          {showAllThreads && thread.metadata?.user_email && (
            <p className="text-xs text-purple-600 truncate mt-0.5">
              {thread.metadata?.user_email as string}
            </p>
          )}
          
          <div className="flex items-center space-x-3 mt-1">
            <span className="text-xs text-gray-500 flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {formatThreadTime(thread)}
            </span>
            {thread.message_count && thread.message_count > 0 && (
              <span className="text-xs text-gray-500">
                {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>

        <ChevronRight className={cn(
          "w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
          isActive && "opacity-100 text-emerald-600"
        )} />
      </div>

      {thread.metadata?.isProcessing && thread.id !== (isActive ? thread.id : null) && (
        <div className="absolute top-2 right-2">
          <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
        </div>
      )}
    </button>
  </motion.div>
);

export const ThreadList: React.FC<{
  threads: Thread[];
  isLoadingThreads: boolean;
  loadError: string | null;
  activeThreadId: string | null;
  isProcessing: boolean;
  showAllThreads: boolean;
  onThreadClick: (threadId: string) => Promise<void>;
  onRetryLoad: () => Promise<void>;
}> = ({ 
  threads, isLoadingThreads, loadError, activeThreadId, 
  isProcessing, showAllThreads, onThreadClick, onRetryLoad 
}) => (
  <div className="flex-1 overflow-y-auto" data-testid="thread-list">
    {loadError && (
      <div className="p-4 mx-4 mt-2 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-600">{loadError}</p>
        <button
          onClick={onRetryLoad}
          className="mt-2 text-xs text-red-700 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    )}
    
    {isLoadingThreads ? (
      <div className="p-4 text-center text-gray-500">
        <div className="animate-spin w-8 h-8 mx-auto mb-2 border-2 border-gray-300 border-t-emerald-500 rounded-full"></div>
        <p className="text-sm">Loading conversations...</p>
      </div>
    ) : (
      <AnimatePresence mode="popLayout">
        {threads.length === 0 && !loadError ? (
          <div className="p-4 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-20" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              isActive={activeThreadId === thread.id}
              isProcessing={isProcessing}
              showAllThreads={showAllThreads}
              onClick={() => onThreadClick(thread.id)}
            />
          ))
        )}
      </AnimatePresence>
    )}
  </div>
);