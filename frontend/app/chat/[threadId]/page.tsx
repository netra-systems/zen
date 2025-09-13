/**
 * Dynamic Thread Chat Page
 * 
 * Handles specific thread navigation with URL state management.
 * Provides deep linking and browser history support.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed component with clear interfaces
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import MainChat from '@/components/chat/MainChat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { validateThreadId } from '@/services/urlSyncService';
import { motion } from 'framer-motion';
import { Loader2, AlertCircle } from 'lucide-react';
import { AuthGuard } from '@/components/AuthGuard';

/**
 * Thread page props from Next.js dynamic routing
 */
interface ThreadPageProps {
  params: Promise<{
    threadId: string;
  }>;
}

/**
 * Loading states for thread initialization
 */
type LoadingState = 'validating' | 'loading' | 'loaded' | 'error';

/**
 * Dynamic thread chat page component
 */
const ThreadPage: React.FC<ThreadPageProps> = ({ params }) => {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loadingState, setLoadingState] = useState<LoadingState>('validating');
  const [errorMessage, setErrorMessage] = useState<string>('');
  
  const router = useRouter();
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const { switchToThread } = useThreadSwitching();
  
  // Handle Promise-based params from Next.js 15
  useEffect(() => {
    params
      .then(({ threadId }) => {
        setThreadId(threadId);
      })
      .catch((error) => {
        setErrorMessage('Failed to load thread parameters');
        setLoadingState('error');
      });
  }, [params]);
  
  useEffect(() => {
    if (threadId) {
      initializeThread(threadId, activeThreadId, switchToThread, setLoadingState, setErrorMessage, router);
    }
  }, [threadId, activeThreadId, switchToThread, router]);
  
  if (loadingState === 'validating' || !threadId) {
    return createValidatingView();
  }
  
  if (loadingState === 'loading') {
    return createLoadingView(threadId);
  }
  
  if (loadingState === 'error') {
    return createErrorView(errorMessage, router);
  }
  
  return (
    <AuthGuard>
      <MainChat />
    </AuthGuard>
  );
};

/**
 * Initializes thread loading and validation
 */
const initializeThread = async (
  threadId: string,
  activeThreadId: string | null,
  switchToThread: (threadId: string) => Promise<boolean>,
  setLoadingState: (state: LoadingState) => void,
  setErrorMessage: (message: string) => void,
  router: ReturnType<typeof useRouter>
): Promise<void> => {
  // Skip if already on correct thread
  if (activeThreadId === threadId) {
    setLoadingState('loaded');
    return;
  }
  
  // Validate thread ID format
  if (!validateThreadId(threadId)) {
    handleInvalidThread(setLoadingState, setErrorMessage, router);
    return;
  }
  
  await loadValidThread(threadId, switchToThread, setLoadingState, setErrorMessage, router);
};

/**
 * Handles invalid thread ID
 */
const handleInvalidThread = (
  setLoadingState: (state: LoadingState) => void,
  setErrorMessage: (message: string) => void,
  router: ReturnType<typeof useRouter>
): void => {
  setErrorMessage('Invalid thread ID format');
  setLoadingState('error');
  
  // Redirect to chat home after delay
  setTimeout(() => router.push('/chat'), 3000);
};

/**
 * Loads valid thread
 */
const loadValidThread = async (
  threadId: string,
  switchToThread: (threadId: string) => Promise<boolean>,
  setLoadingState: (state: LoadingState) => void,
  setErrorMessage: (message: string) => void,
  router: ReturnType<typeof useRouter>
): Promise<void> => {
  setLoadingState('loading');
  
  try {
    const success = await switchToThread(threadId);
    
    if (success) {
      setLoadingState('loaded');
    } else {
      handleThreadLoadError(setLoadingState, setErrorMessage, router);
    }
  } catch (error) {
    handleThreadLoadError(setLoadingState, setErrorMessage, router);
  }
};

/**
 * Handles thread loading errors
 */
const handleThreadLoadError = (
  setLoadingState: (state: LoadingState) => void,
  setErrorMessage: (message: string) => void,
  router: ReturnType<typeof useRouter>
): void => {
  setErrorMessage('Failed to load conversation. Redirecting to chat home...');
  setLoadingState('error');
  
  // Redirect to chat home after delay
  setTimeout(() => router.push('/chat'), 3000);
};

/**
 * Creates validating view
 */
const createValidatingView = (): JSX.Element => {
  return (
    <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        <div className="text-sm text-gray-600">Validating thread...</div>
      </div>
    </div>
  );
};

/**
 * Creates loading view with thread info
 */
const createLoadingView = (threadId: string): JSX.Element => {
  return (
    <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-4 p-6 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm"
      >
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <div className="text-sm text-gray-600">Loading conversation...</div>
        <div className="text-xs text-gray-400">
          Thread: {threadId.slice(0, 8)}...
        </div>
      </motion.div>
    </div>
  );
};

/**
 * Creates error view with message
 */
const createErrorView = (
  errorMessage: string,
  router: ReturnType<typeof useRouter>
): JSX.Element => {
  return (
    <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center gap-4 p-6 bg-red-50 rounded-lg shadow-sm max-w-md text-center"
      >
        <AlertCircle className="h-12 w-12 text-red-500" />
        <div className="text-lg font-semibold text-red-900">
          Unable to Load Conversation
        </div>
        <div className="text-sm text-red-700">{errorMessage}</div>
        <button
          onClick={() => router.push('/chat')}
          className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Return to Chat
        </button>
      </motion.div>
    </div>
  );
};

export default ThreadPage;