"use client";

import React from 'react';
import { Loader2, AlertCircle, RefreshCw, Clock } from 'lucide-react';
import type { ThreadLoadingState, ThreadError } from '@/types/thread-error-types';

/**
 * Thread Loading Indicator Props
 */
interface ThreadLoadingIndicatorProps {
  readonly state: ThreadLoadingState;
  readonly threadId?: string;
  readonly error?: ThreadError | null;
  readonly retryCount?: number;
  readonly maxRetries?: number;
  readonly onRetry?: () => void;
  readonly showDetails?: boolean;
}

/**
 * Loading indicator component for thread operations
 */
export const ThreadLoadingIndicator: React.FC<ThreadLoadingIndicatorProps> = ({
  state,
  threadId,
  error,
  retryCount = 0,
  maxRetries = 3,
  onRetry,
  showDetails = false
}) => {
  if (state === 'idle' || state === 'success') {
    return null;
  }

  return (
    <div className={getContainerClassName(state)}>
      <div className="flex items-center gap-2">
        {renderStateIcon(state)}
        
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium">
            {getStateMessage(state, threadId)}
          </div>
          
          {showDetails && renderDetails(state, error, retryCount, maxRetries)}
        </div>

        {state === 'error' && canRetry(retryCount, maxRetries) && onRetry && (
          <button
            onClick={onRetry}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Retry loading"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

/**
 * Gets container class name based on state
 */
const getContainerClassName = (state: ThreadLoadingState): string => {
  const baseClasses = 'p-2 rounded-lg border';
  
  switch (state) {
    case 'loading':
      return `${baseClasses} bg-blue-50 border-blue-200`;
    case 'retrying':
      return `${baseClasses} bg-yellow-50 border-yellow-200`;
    case 'error':
      return `${baseClasses} bg-red-50 border-red-200`;
    case 'timeout':
      return `${baseClasses} bg-orange-50 border-orange-200`;
    case 'aborted':
      return `${baseClasses} bg-gray-50 border-gray-200`;
    default:
      return `${baseClasses} bg-gray-50 border-gray-200`;
  }
};

/**
 * Renders state-appropriate icon
 */
const renderStateIcon = (state: ThreadLoadingState): React.ReactNode => {
  switch (state) {
    case 'loading':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    case 'retrying':
      return <RefreshCw className="w-4 h-4 text-yellow-500 animate-spin" />;
    case 'error':
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    case 'timeout':
      return <Clock className="w-4 h-4 text-orange-500" />;
    case 'aborted':
      return <AlertCircle className="w-4 h-4 text-gray-500" />;
    default:
      return <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />;
  }
};

/**
 * Gets state message for user
 */
const getStateMessage = (state: ThreadLoadingState, threadId?: string): string => {
  const threadName = threadId ? `thread ${threadId.slice(0, 8)}...` : 'thread';
  
  switch (state) {
    case 'loading':
      return `Loading ${threadName}`;
    case 'retrying':
      return `Retrying ${threadName}`;
    case 'error':
      return `Failed to load ${threadName}`;
    case 'timeout':
      return `Loading ${threadName} timed out`;
    case 'aborted':
      return `Loading ${threadName} was cancelled`;
    default:
      return `Processing ${threadName}`;
  }
};

/**
 * Renders additional details for state
 */
const renderDetails = (
  state: ThreadLoadingState,
  error: ThreadError | null | undefined,
  retryCount: number,
  maxRetries: number
): React.ReactNode => {
  if (state === 'error' && error) {
    return (
      <div className="text-xs text-red-600 mt-1">
        {error.message}
        {retryCount > 0 && (
          <span className="ml-2">
            (Retry {retryCount}/{maxRetries})
          </span>
        )}
      </div>
    );
  }

  if (state === 'retrying') {
    return (
      <div className="text-xs text-yellow-600 mt-1">
        Attempt {retryCount + 1} of {maxRetries}
      </div>
    );
  }

  return null;
};

/**
 * Checks if retry is possible
 */
const canRetry = (retryCount: number, maxRetries: number): boolean => {
  return retryCount < maxRetries;
};

export default ThreadLoadingIndicator;