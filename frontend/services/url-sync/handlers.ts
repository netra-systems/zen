/**
 * URL Sync Handlers Module
 * 
 * Event handlers and sync operations for URL synchronization.
 * Manages bidirectional sync between URL and store state.
 * 
 * @compliance conventions.xml - Handlers module under 300 lines, max 8 lines per function
 * @compliance type_safety.xml - Strongly typed handler functions
 */

import type { 
  UrlSyncConfig, 
  UrlSyncState, 
  StateSetter, 
  ThreadSwitchFunction 
} from './types';
import { 
  createUrlWithThread, 
  extractThreadIdFromUrl, 
  shouldSyncUrl,
  isValidThreadId,
  createErrorUpdate,
  createSuccessUpdate
} from './utils';

/**
 * Initializes URL sync on mount
 */
export const initializeUrlSync = (
  config: UrlSyncConfig,
  searchParams: URLSearchParams,
  activeThreadId: string | null,
  setState: StateSetter,
  switchToThread: ThreadSwitchFunction
): void => {
  if (!config.enabled) return;
  
  const urlThreadId = searchParams.get(config.paramName);
  
  if (urlThreadId && urlThreadId !== activeThreadId) {
    performInitialThreadSwitch(urlThreadId, switchToThread, setState);
  }
  
  setState(prev => ({ ...prev, isInitialized: true }));
};

/**
 * Handles store to URL synchronization
 */
export const handleStoreToUrlSync = (
  activeThreadId: string | null,
  config: UrlSyncConfig,
  pathname: string,
  router: any,
  lastSyncedRef: React.MutableRefObject<string | null>,
  isUpdatingRef: React.MutableRefObject<boolean>
): void => {
  if (!shouldSyncUrl(config, pathname, isUpdatingRef.current)) return;
  
  if (activeThreadId !== lastSyncedRef.current) {
    updateUrlFromStore(activeThreadId, config, router, lastSyncedRef);
  }
};

/**
 * Handles URL to store synchronization
 */
export const handleUrlToStoreSync = (
  searchParams: URLSearchParams,
  config: UrlSyncConfig,
  switchToThread: ThreadSwitchFunction,
  lastSyncedRef: React.MutableRefObject<string | null>,
  isUpdatingRef: React.MutableRefObject<boolean>,
  setState: StateSetter
): void => {
  if (!config.enabled || isUpdatingRef.current) return;
  
  const urlThreadId = searchParams.get(config.paramName);
  
  if (urlThreadId && urlThreadId !== lastSyncedRef.current) {
    updateStoreFromUrl(urlThreadId, switchToThread, lastSyncedRef, setState);
  }
};

/**
 * Performs initial thread switch from URL
 */
export const performInitialThreadSwitch = async (
  threadId: string,
  switchToThread: ThreadSwitchFunction,
  setState: StateSetter
): Promise<void> => {
  try {
    setState(prev => ({ ...prev, pendingNavigation: threadId }));
    const success = await switchToThread(threadId);
    
    if (!success) {
      setState(createErrorUpdate('Thread not found or access denied'));
    }
  } catch (error) {
    setState(createErrorUpdate('Failed to load thread'));
  } finally {
    setState(prev => ({ ...prev, pendingNavigation: null }));
  }
};

/**
 * Updates URL from store changes
 */
export const updateUrlFromStore = (
  activeThreadId: string | null,
  config: UrlSyncConfig,
  router: any,
  lastSyncedRef: React.MutableRefObject<string | null>
): void => {
  const url = createUrlWithThread(activeThreadId, config);
  
  router.replace(url, { scroll: false });
  lastSyncedRef.current = activeThreadId;
};

/**
 * Updates store from URL changes
 */
export const updateStoreFromUrl = async (
  threadId: string,
  switchToThread: ThreadSwitchFunction,
  lastSyncedRef: React.MutableRefObject<string | null>,
  setState: StateSetter
): Promise<void> => {
  setState(prev => ({ ...prev, pendingNavigation: threadId, validationError: null }));
  
  try {
    const success = await switchToThread(threadId);
    
    if (success) {
      lastSyncedRef.current = threadId;
      setState(createSuccessUpdate(threadId));
    } else {
      setState(createErrorUpdate('Thread not accessible'));
    }
  } catch (error) {
    setState(createErrorUpdate('Failed to switch thread'));
  }
};

/**
 * Performs URL to store sync operation
 */
export const performUrlToStoreSync = async (
  url: string,
  config: UrlSyncConfig,
  switchToThread: ThreadSwitchFunction,
  setState: StateSetter
): Promise<boolean> => {
  const threadId = extractThreadIdFromUrl(url, config);
  
  if (!isValidThreadId(threadId)) return false;
  
  setState(prev => ({ ...prev, pendingNavigation: threadId, validationError: null }));
  
  try {
    const success = await switchToThread(threadId);
    
    if (success) {
      setState(createSuccessUpdate(threadId));
    } else {
      setState(createErrorUpdate('Invalid thread ID'));
    }
    
    return success;
  } catch (error) {
    setState(createErrorUpdate('Invalid thread ID'));
    return false;
  }
};

/**
 * Performs store to URL sync operation
 */
export const performStoreToUrlSync = (
  threadId: string | null,
  config: UrlSyncConfig,
  router: any,
  lastSyncedRef: React.MutableRefObject<string | null>
): void => {
  if (!config.enabled) return;
  
  const url = createUrlWithThread(threadId, config);
  router.replace(url, { scroll: false });
  lastSyncedRef.current = threadId;
};