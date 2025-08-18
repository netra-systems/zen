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
import { useThreadSwitching } from '@/hooks/useThreadSwitching';
import { useEffect, useCallback, useRef, useState } from 'react';
import { 
  urlSyncTypes, 
  urlSyncUtils, 
  urlSyncHandlers 
} from './url-sync';

/**
 * URL synchronization hook
 */
export const useUrlSync = (config: Partial<urlSyncTypes.UrlSyncConfig> = {}): urlSyncTypes.UseUrlSyncResult => {
  const fullConfig = { ...urlSyncTypes.DEFAULT_CONFIG, ...config };
  const [state, setState] = useState<urlSyncTypes.UrlSyncState>(urlSyncUtils.createInitialSyncState());
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  
  const activeThreadId = useUnifiedChatStore(state => state.activeThreadId);
  const { switchToThread } = useThreadSwitching();
  
  const lastSyncedRef = useRef<string | null>(null);
  const isUpdatingRef = useRef(false);

  // Initialize URL sync on mount
  useEffect(() => {
    urlSyncHandlers.initializeUrlSync(fullConfig, searchParams, activeThreadId, setState, switchToThread);
  }, []);

  // Listen to store changes and update URL
  useEffect(() => {
    urlSyncHandlers.handleStoreToUrlSync(activeThreadId, fullConfig, pathname, router, lastSyncedRef, isUpdatingRef);
  }, [activeThreadId, pathname, router]);

  // Listen to URL changes and update store
  useEffect(() => {
    urlSyncHandlers.handleUrlToStoreSync(searchParams, fullConfig, switchToThread, lastSyncedRef, isUpdatingRef, setState);
  }, [searchParams, switchToThread]);

  const syncUrlToStore = useCallback(async (url: string): Promise<boolean> => {
    return await urlSyncHandlers.performUrlToStoreSync(url, fullConfig, switchToThread, setState);
  }, [switchToThread]);

  const syncStoreToUrl = useCallback((threadId: string | null): void => {
    urlSyncHandlers.performStoreToUrlSync(threadId, fullConfig, router, lastSyncedRef);
  }, [router]);

  const validateThreadId = useCallback(async (threadId: string): Promise<boolean> => {
    return await urlSyncUtils.performThreadValidation(threadId);
  }, []);

  return { state, syncUrlToStore, syncStoreToUrl, validateThreadId };
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

// Re-export types for convenience
export type { 
  UrlSyncConfig,
  UrlSyncState,
  UseUrlSyncResult 
} from './url-sync/types';