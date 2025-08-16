"use client";

import React from 'react';
import { RefreshCw, AlertTriangle, MessageSquare } from 'lucide-react';

/**
 * Thread Error Fallback Props
 */
interface ThreadErrorFallbackProps {
  readonly error?: Error;
  readonly threadId?: string;
  readonly retryCount: number;
  readonly maxRetries: number;
  readonly onRetry: () => void;
  readonly onReset: () => void;
}

/**
 * Error fallback component for thread operations
 */
export const ThreadErrorFallback: React.FC<ThreadErrorFallbackProps> = ({
  error,
  threadId,
  retryCount,
  maxRetries,
  onRetry,
  onReset
}) => {
  const canRetry = retryCount < maxRetries;
  const errorMessage = getErrorMessage(error);
  const errorSeverity = getErrorSeverity(error);

  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
        
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-red-800 mb-1">
            Thread Loading Error
          </h3>
          
          <p className="text-sm text-red-700 mb-3">
            {errorMessage}
          </p>

          {threadId && (
            <p className="text-xs text-red-600 mb-3">
              Thread ID: {threadId}
            </p>
          )}

          <div className="flex items-center gap-2">
            {canRetry && (
              <button
                onClick={onRetry}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Retry ({retryCount}/{maxRetries})
              </button>
            )}
            
            <button
              onClick={onReset}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
            >
              <MessageSquare className="w-3 h-3" />
              Reset
            </button>
          </div>

          {!canRetry && (
            <div className="mt-2 text-xs text-red-600">
              Maximum retry attempts reached. Please reset or refresh the page.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Gets user-friendly error message
 */
const getErrorMessage = (error?: Error): string => {
  if (!error) return 'An unknown error occurred';
  
  if (error.message.includes('timeout')) {
    return 'Thread loading timed out. Please check your connection.';
  }
  
  if (error.message.includes('network')) {
    return 'Network error occurred. Please check your connection.';
  }
  
  if (error.message.includes('abort')) {
    return 'Thread loading was cancelled.';
  }
  
  return error.message || 'Failed to load thread';
};

/**
 * Determines error severity level
 */
const getErrorSeverity = (error?: Error): 'low' | 'medium' | 'high' => {
  if (!error) return 'medium';
  
  if (error.message.includes('timeout') || error.message.includes('network')) {
    return 'medium';
  }
  
  if (error.message.includes('abort')) {
    return 'low';
  }
  
  return 'high';
};

export default ThreadErrorFallback;