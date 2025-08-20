/**
 * OptimisticMessage Component - Ultra-fast message rendering with skeletons
 * 
 * Handles pending, processing, and failed message states with graceful loading
 * and retry functionality. Provides instant feedback for optimistic updates.
 * 
 * BUSINESS VALUE JUSTIFICATION (BVJ):
 * - Segment: Growth & Enterprise
 * - Goal: Instant feedback improves perceived performance
 * - Impact: Better UX increases user engagement and retention
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, AlertCircle, RefreshCw, Send, Bot } from 'lucide-react';
import type { OptimisticMessage, OptimisticStatus } from '@/services/optimistic-updates';

// ============================================================================
// Component Props and Types
// ============================================================================

export interface OptimisticMessageProps {
  message: OptimisticMessage;
  onRetry?: (messageId: string) => Promise<void>;
  className?: string;
  showAvatar?: boolean;
}

interface LoadingSkeletonProps {
  type: 'user' | 'assistant';
  animate?: boolean;
}

interface RetryButtonProps {
  onRetry: () => Promise<void>;
  isRetrying: boolean;
}

// ============================================================================
// Loading Skeleton Component (25-line functions)
// ============================================================================

const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({ type, animate = true }) => {
  const baseClasses = "animate-pulse bg-gray-200 rounded";
  const heightClass = type === 'user' ? 'h-4' : 'h-6';
  
  return (
    <div className="space-y-2">
      <div className={`${baseClasses} ${heightClass} w-3/4`} />
      <div className={`${baseClasses} h-4 w-1/2`} />
      {animate && <div className={`${baseClasses} h-4 w-2/3`} />}
    </div>
  );
};

// ============================================================================
// Retry Button Component (25-line functions)
// ============================================================================

const RetryButton: React.FC<RetryButtonProps> = ({ onRetry, isRetrying }) => {
  const [isClicked, setIsClicked] = useState(false);
  
  const handleClick = useCallback(async () => {
    setIsClicked(true);
    try {
      await onRetry();
    } finally {
      setIsClicked(false);
    }
  }, [onRetry]);

  return (
    <motion.button
      onClick={handleClick}
      disabled={isRetrying || isClicked}
      className="flex items-center gap-2 px-3 py-1 text-sm text-red-600 hover:text-red-700 
                 bg-red-50 hover:bg-red-100 rounded-md border border-red-200 
                 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <RefreshCw className={`h-3 w-3 ${(isRetrying || isClicked) ? 'animate-spin' : ''}`} />
      {isRetrying ? 'Retrying...' : 'Retry'}
    </motion.button>
  );
};

// ============================================================================
// Status Indicator Component (25-line functions)
// ============================================================================

const StatusIndicator: React.FC<{ status: OptimisticStatus }> = ({ status }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'pending': return { icon: Send, color: 'text-blue-500', label: 'Sending...' };
      case 'processing': return { icon: Bot, color: 'text-green-500', label: 'AI thinking...' };
      case 'failed': return { icon: AlertCircle, color: 'text-red-500', label: 'Failed' };
      case 'retrying': return { icon: RefreshCw, color: 'text-yellow-500', label: 'Retrying...' };
      default: return { icon: Loader2, color: 'text-gray-500', label: 'Processing...' };
    }
  };

  const { icon: Icon, color, label } = getStatusConfig();
  const shouldSpin = status === 'processing' || status === 'retrying';
  
  return (
    <div className={`flex items-center gap-1 text-xs ${color}`}>
      <Icon className={`h-3 w-3 ${shouldSpin ? 'animate-spin' : ''}`} />
      <span>{label}</span>
    </div>
  );
};

// ============================================================================
// Message Avatar Component (25-line functions)
// ============================================================================

const MessageAvatar: React.FC<{ role: 'user' | 'assistant' }> = ({ role }) => {
  const isUser = role === 'user';
  const bgColor = isUser ? 'bg-blue-500' : 'bg-green-500';
  const icon = isUser ? 'U' : 'AI';
  
  return (
    <div className={`w-8 h-8 rounded-full ${bgColor} flex items-center justify-center 
                     text-white text-sm font-medium flex-shrink-0`}>
      {icon}
    </div>
  );
};

// ============================================================================
// Content Renderer Component (25-line functions)
// ============================================================================

const MessageContent: React.FC<{ message: OptimisticMessage }> = ({ message }) => {
  const hasContent = message.content && message.content.trim().length > 0;
  const isProcessing = message.status === 'processing';
  const shouldShowSkeleton = !hasContent && isProcessing;
  
  if (shouldShowSkeleton) {
    return <LoadingSkeleton type={message.role} />;
  }
  
  return (
    <div className="prose prose-sm max-w-none">
      {hasContent ? (
        <p className="whitespace-pre-wrap">{message.content}</p>
      ) : (
        <p className="text-gray-500 italic">Message pending...</p>
      )}
    </div>
  );
};

// ============================================================================
// Main OptimisticMessage Component (25-line functions)
// ============================================================================

export const OptimisticMessage: React.FC<OptimisticMessageProps> = ({
  message,
  onRetry,
  className = '',
  showAvatar = true
}) => {
  const [isRetrying, setIsRetrying] = useState(false);
  
  const handleRetry = useCallback(async () => {
    if (!onRetry) return;
    setIsRetrying(true);
    try {
      await onRetry(message.localId);
    } finally {
      setIsRetrying(false);
    }
  }, [onRetry, message.localId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.15 }}
      className={`flex gap-3 p-4 ${className}`}
    >
      {showAvatar && <MessageAvatar role={message.role} />}
      <div className="flex-1 min-w-0">
        <MessageHeader message={message} />
        <MessageContent message={message} />
        <MessageFooter message={message} onRetry={handleRetry} isRetrying={isRetrying} />
      </div>
    </motion.div>
  );
};

// ============================================================================
// Message Header Component (25-line functions)
// ============================================================================

const MessageHeader: React.FC<{ message: OptimisticMessage }> = ({ message }) => {
  const timestamp = new Date(message.timestamp || Date.now()).toLocaleTimeString();
  const roleName = message.role === 'user' ? 'You' : 'Assistant';
  
  return (
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm font-medium text-gray-900">{roleName}</span>
      <div className="flex items-center gap-2">
        <StatusIndicator status={message.status} />
        <span className="text-xs text-gray-500">{timestamp}</span>
      </div>
    </div>
  );
};

// ============================================================================
// Message Footer Component (25-line functions)
// ============================================================================

const MessageFooter: React.FC<{
  message: OptimisticMessage;
  onRetry: () => Promise<void>;
  isRetrying: boolean;
}> = ({ message, onRetry, isRetrying }) => {
  const showRetry = message.status === 'failed';
  
  if (!showRetry) {
    return null;
  }
  
  return (
    <div className="mt-2 flex items-center gap-2">
      <RetryButton onRetry={onRetry} isRetrying={isRetrying} />
      <span className="text-xs text-gray-500">
        Message failed to send. Click retry to try again.
      </span>
    </div>
  );
};

// ============================================================================
// Optimistic Message List Component (25-line functions)
// ============================================================================

export interface OptimisticMessageListProps {
  messages: OptimisticMessage[];
  onRetry?: (messageId: string) => Promise<void>;
  className?: string;
}

export const OptimisticMessageList: React.FC<OptimisticMessageListProps> = ({
  messages,
  onRetry,
  className = ''
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <AnimatePresence mode="wait">
        {messages.map((message) => (
          <OptimisticMessage
            key={message.localId}
            message={message}
            onRetry={onRetry}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default OptimisticMessage;