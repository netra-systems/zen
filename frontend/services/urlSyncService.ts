/**
 * URL Synchronization Service
 * 
 * Provides two-way binding between URL state and thread store.
 * Enables browser history navigation and shareable links for collaboration.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed service with clear interfaces
 */

import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useEffect, useCallback, useRef, useState } from 'react';
import { 
  urlSyncTypes, 
  urlSyncUtils, 
  urlSyncHandlers 
} from './url-sync';

/**
 * URL synchronization hook - handles ONLY URL state management
 */
export const useURLSync = (config: Partial<urlSyncTypes.UrlSyncConfig> = {}): urlSyncTypes.UseUrlSyncResult => {
  const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
  const [state, setState] = useState<urlSyncTypes.UrlSyncState>(urlSyncUtils.createInitialSyncState());
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  
  const lastSyncedRef = useRef<string | null>(null);
  const isUpdatingRef = useRef(false);
  const isManualUpdateRef = useRef(false);

  // Listen to store changes and update URL (skip during manual updates)
  useEffect(() => {
    if (!isManualUpdateRef.current) {
      urlSyncHandlers.handleStoreToUrlSync(activeThreadId, fullConfig, pathname, router, lastSyncedRef, isUpdatingRef);
    }
  }, [activeThreadId, pathname, router]);

  const syncUrlToStore = useCallback(async (url: string, switchToThread?: urlSyncTypes.ThreadSwitchFunction): Promise<boolean> => {
    if (!switchToThread) return false;
    return await urlSyncHandlers.performUrlToStoreSync(url, fullConfig, switchToThread, setState);
  }, []);

  const syncStoreToUrl = useCallback((threadId: string | null): void => {
    // Set manual update flag to prevent auto-sync race condition
    isManualUpdateRef.current = true;
    urlSyncHandlers.performStoreToUrlSync(threadId, fullConfig, router, lastSyncedRef);
    // Clear flag after a short delay to re-enable auto-sync
    setTimeout(() => {
      isManualUpdateRef.current = false;
    }, 100);
  }, [router]);

  const validateThreadId = useCallback(async (threadId: string): Promise<boolean> => {
    return await urlSyncUtils.performThreadValidation(threadId);
  }, []);

  return { 
    state, 
    syncUrlToStore, 
    syncStoreToUrl, 
    validateThreadId,
    // Aliases for backward compatibility
    updateUrl: syncStoreToUrl,
    currentThreadId: searchParams?.get(fullConfig.paramName) ?? null,
    navigateToThread: (threadId: string) => syncStoreToUrl(threadId),
    navigateToChat: () => syncStoreToUrl(null)
  };
};

/**
 * URL sync with thread switching integration hook
 */
export const useURLSyncWithThreadSwitching = (
  config: Partial<urlSyncTypes.UrlSyncConfig> = {},
  switchToThread: urlSyncTypes.ThreadSwitchFunction
): urlSyncTypes.UseUrlSyncResult & { 
  initializeFromUrl: () => void;
  syncFromUrl: () => void;
} => {
  const urlSync = useURLSync(config);
  const searchParams = useSearchParams();
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
  
  const initializeFromUrl = useCallback(() => {
    if (!fullConfig.enabled) return;
    const urlThreadId = searchParams.get(fullConfig.paramName);
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchToThread(urlThreadId);
    }
  }, [searchParams, activeThreadId, switchToThread, fullConfig]);
  
  const syncFromUrl = useCallback(() => {
    if (!fullConfig.enabled) return;
    const urlThreadId = searchParams.get(fullConfig.paramName);
    if (urlThreadId && urlThreadId !== activeThreadId) {
      switchToThread(urlThreadId);
    }
  }, [searchParams, activeThreadId, switchToThread, fullConfig]);
  
  // Initialize URL sync on mount
  useEffect(() => {
    initializeFromUrl();
  }, []);
  
  // Listen to URL changes
  useEffect(() => {
    syncFromUrl();
  }, [searchParams]);
  
  return {
    ...urlSync,
    initializeFromUrl,
    syncFromUrl
  };
};

/**
 * URL sync service for imperative use
 */
export const urlSyncService = {
  /**
   * Updates URL with thread ID
   */
  updateUrl: (threadId: string | null, config: Partial<urlSyncTypes.UrlSyncConfig> = {}): void => {
    const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
    
    if (typeof window !== 'undefined') {
      const url = urlSyncUtils.createUrlWithThread(threadId, fullConfig);
      window.history.replaceState(null, '', url);
    }
  },

  /**
   * Gets thread ID from current URL
   */
  getThreadIdFromUrl: (config: Partial<urlSyncTypes.UrlSyncConfig> = {}): string | null => {
    const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
    
    if (typeof window !== 'undefined') {
      return urlSyncUtils.extractThreadIdFromUrl(window.location.href, fullConfig);
    }
    
    return null;
  },

  /**
   * Creates shareable URL for thread
   */
  createShareableUrl: (threadId: string, config: Partial<urlSyncTypes.UrlSyncConfig> = {}): string => {
    const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
    
    if (typeof window !== 'undefined') {
      return urlSyncUtils.createUrlWithThread(threadId, fullConfig);
    }
    
    return `${fullConfig.basePath}?${fullConfig.paramName}=${threadId}`;
  }
};

/**
 * Browser history sync hook
 */
export const useBrowserHistorySync = (onHistoryChange: (threadId: string | null) => void): void => {
  useEffect(() => {
    const handlePopState = () => {
      const threadId = urlSyncService.getThreadIdFromUrl();
      onHistoryChange(threadId);
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [onHistoryChange]);
};

/**
 * Standalone thread ID validation function
 */
export const validateThreadId = async (threadId: string): Promise<boolean> => {
  return await urlSyncUtils.performThreadValidation(threadId);
};

/**
 * Handle deep link navigation
 */
export const handleDeepLink = (threadId: string, onNavigate: (id: string) => void): void => {
  if (threadId && urlSyncUtils.performThreadValidation(threadId)) {
    onNavigate(threadId);
  }
};

// Re-export types for convenience
export type { 
  UrlSyncConfig,
  UrlSyncState,
  UseUrlSyncResult 
} from './url-sync/types';