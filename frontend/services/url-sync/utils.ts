/**
 * URL Sync Utils Module
 * 
 * Utility functions for URL manipulation and validation.
 * Provides core functionality for URL synchronization operations.
 * 
 * @compliance conventions.xml - Utils module under 300 lines, max 8 lines per function
 * @compliance type_safety.xml - Strongly typed utility functions
 */

import type { UrlSyncConfig, UrlSyncState } from './types';

/**
 * Creates initial sync state
 */
export const createInitialSyncState = (): UrlSyncState => {
  return {
    isInitialized: false,
    lastSyncedThreadId: null,
    pendingNavigation: null,
    validationError: null
  };
};

/**
 * Creates URL with thread parameter
 */
export const createUrlWithThread = (threadId: string | null, config: UrlSyncConfig): string => {
  const url = new URL(config.basePath, window.location.origin);
  
  if (threadId) {
    url.searchParams.set(config.paramName, threadId);
  }
  
  return url.pathname + url.search;
};

/**
 * Extracts thread ID from URL
 */
export const extractThreadIdFromUrl = (url: string, config: UrlSyncConfig): string | null => {
  try {
    const urlObj = new URL(url, window.location.origin);
    return urlObj.searchParams.get(config.paramName);
  } catch {
    return null;
  }
};

/**
 * Validates thread access
 */
export const performThreadValidation = async (threadId: string): Promise<boolean> => {
  // This would typically make an API call to validate access
  // For now, basic validation - non-empty string
  return threadId && threadId.trim().length > 0;
};

/**
 * Checks if URL sync should be active
 */
export const shouldSyncUrl = (
  config: UrlSyncConfig, 
  pathname: string, 
  isUpdating: boolean
): boolean => {
  return config.enabled && pathname === config.basePath && !isUpdating;
};

/**
 * Validates thread ID format
 */
export const isValidThreadId = (threadId: string | null): threadId is string => {
  return typeof threadId === 'string' && threadId.trim().length > 0;
};

/**
 * Creates error state update
 */
export const createErrorUpdate = (error: string) => (prev: UrlSyncState): UrlSyncState => {
  return { ...prev, validationError: error, pendingNavigation: null };
};

/**
 * Creates success state update
 */
export const createSuccessUpdate = (threadId: string) => (prev: UrlSyncState): UrlSyncState => {
  return { ...prev, validationError: null, pendingNavigation: null, lastSyncedThreadId: threadId };
};