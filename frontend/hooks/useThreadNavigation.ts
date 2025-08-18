/**
 * Thread Navigation Hook
 * 
 * Provides URL-aware thread navigation with browser history support.
 * Handles deep linking and coordinates with thread switching.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed hook with clear interfaces
 */

import { useEffect, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { 
  useURLSync, 
  useBrowserHistorySync, 
  validateThreadId 
} from '@/services/urlSyncService';

/**
 * Thread navigation configuration
 */
export interface ThreadNavigationConfig {
  readonly enableDeepLinking: boolean;
  readonly enableHistorySync: boolean;
  readonly fallbackToHome: boolean;
}

/**
 * Thread navigation result
 */
export interface ThreadNavigationResult {
  readonly currentThreadId: string | null;
  readonly isNavigating: boolean;
  readonly navigateToThread: (threadId: string) => Promise<boolean>;
  readonly navigateToHome: () => void;
}

/**
 * Default navigation configuration
 */
const DEFAULT_CONFIG: ThreadNavigationConfig = {
  enableDeepLinking: true,
  enableHistorySync: true,
  fallbackToHome: true
};

/**
 * Thread navigation hook with URL awareness
 */
export const useThreadNavigation = (
  config: Partial<ThreadNavigationConfig> = {}
): ThreadNavigationResult => {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };
  const pathname = usePathname();
  
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const isThreadLoading = useUnifiedChatStore(state => state.isThreadLoading);
  
  const { switchToThread } = useThreadSwitching();
  const { currentThreadId, navigateToThread, navigateToChat } = useURLSync();
  
  // Handle browser history changes
  const handleHistoryChange = useCallback((threadId: string | null) => {
    handleBrowserHistoryNavigation(threadId, activeThreadId, switchToThread, mergedConfig);
  }, [activeThreadId, switchToThread, mergedConfig]);
  
  // Set up browser history sync if enabled
  if (mergedConfig.enableHistorySync) {
    useBrowserHistorySync(handleHistoryChange);
  }
  
  // Handle deep linking on mount
  useEffect(() => {
    handleDeepLinkOnMount(currentThreadId, activeThreadId, switchToThread, mergedConfig);
  }, []); // Run only on mount
  
  const navigateToThreadWithLoading = useCallback(async (threadId: string): Promise<boolean> => {
    return await navigateToThreadSafely(threadId, switchToThread, navigateToThread);
  }, [switchToThread, navigateToThread]);
  
  const navigateToHome = useCallback(() => {
    navigateToChat();
  }, [navigateToChat]);
  
  return {
    currentThreadId,
    isNavigating: isThreadLoading,
    navigateToThread: navigateToThreadWithLoading,
    navigateToHome
  };
};

/**
 * Handles browser history navigation
 */
const handleBrowserHistoryNavigation = async (
  urlThreadId: string | null,
  activeThreadId: string | null,
  switchToThread: (threadId: string, options?: any) => Promise<boolean>,
  config: ThreadNavigationConfig
): Promise<void> => {
  // Skip if already on the correct thread
  if (urlThreadId === activeThreadId) return;
  
  if (urlThreadId && validateThreadId(urlThreadId)) {
    // Load thread from URL
    await switchToThread(urlThreadId, { skipUrlUpdate: true });
  } else if (config.fallbackToHome && activeThreadId) {
    // Clear active thread when navigating to home
    // This will be handled by the store
  }
};

/**
 * Handles deep linking on component mount
 */
const handleDeepLinkOnMount = async (
  urlThreadId: string | null,
  activeThreadId: string | null,
  switchToThread: (threadId: string, options?: any) => Promise<boolean>,
  config: ThreadNavigationConfig
): Promise<void> => {
  if (!config.enableDeepLinking) return;
  
  // If URL has a thread ID and it's different from active thread
  if (urlThreadId && urlThreadId !== activeThreadId) {
    if (validateThreadId(urlThreadId)) {
      await switchToThread(urlThreadId, { skipUrlUpdate: true });
    }
  }
};

/**
 * Safely navigates to thread with error handling
 */
const navigateToThreadSafely = async (
  threadId: string,
  switchToThread: (threadId: string) => Promise<boolean>,
  navigateToThread: (threadId: string) => void
): Promise<boolean> => {
  if (!validateThreadId(threadId)) {
    console.error('Invalid thread ID format:', threadId);
    return false;
  }
  
  try {
    const success = await switchToThread(threadId);
    
    if (success) {
      // URL will be updated by the switchToThread hook
      return true;
    } else {
      console.error('Failed to load thread:', threadId);
      return false;
    }
  } catch (error) {
    console.error('Error navigating to thread:', error);
    return false;
  }
};

/**
 * Creates shareable thread URL
 */
export const createThreadShareUrl = (threadId: string): string | null => {
  if (!validateThreadId(threadId)) return null;
  
  const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
  return `${baseUrl}/chat/${threadId}`;
};

/**
 * Extracts thread ID from current URL
 */
export const getCurrentThreadFromUrl = (): string | null => {
  if (typeof window === 'undefined') return null;
  
  const pathname = window.location.pathname;
  const match = pathname.match(/^\/chat\/([^\/]+)$/);
  return match ? match[1] : null;
};