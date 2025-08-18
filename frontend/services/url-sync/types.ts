/**
 * URL Sync Types Module
 * 
 * Type definitions for URL synchronization service.
 * Provides strongly typed interfaces for all URL sync operations.
 * 
 * @compliance conventions.xml - Types module under 300 lines, max 8 lines per function
 * @compliance type_safety.xml - Complete type safety for all interfaces
 */

/**
 * URL sync configuration
 */
export interface UrlSyncConfig {
  readonly enabled: boolean;
  readonly paramName: string;
  readonly basePath: string;
  readonly validateThreadAccess: boolean;
}

/**
 * URL sync state
 */
export interface UrlSyncState {
  readonly isInitialized: boolean;
  readonly lastSyncedThreadId: string | null;
  readonly pendingNavigation: string | null;
  readonly validationError: string | null;
}

/**
 * URL sync service result
 */
export interface UseUrlSyncResult {
  readonly state: UrlSyncState;
  readonly syncUrlToStore: (url: string) => Promise<boolean>;
  readonly syncStoreToUrl: (threadId: string | null) => void;
  readonly validateThreadId: (threadId: string) => Promise<boolean>;
  // Aliases for backward compatibility
  readonly updateUrl: (threadId: string | null) => void;
  readonly currentThreadId: string | null;
  readonly navigateToThread: (threadId: string) => void;
  readonly navigateToChat: () => void;
}

/**
 * State setter function type
 */
export type StateSetter = (updater: (prev: UrlSyncState) => UrlSyncState) => void;

/**
 * Thread switch function type
 */
export type ThreadSwitchFunction = (threadId: string) => Promise<boolean>;

/**
 * Default configuration
 */
export const DEFAULT_CONFIG: UrlSyncConfig = {
  enabled: true,
  paramName: 'thread',
  basePath: '/chat',
  validateThreadAccess: true
};