/**
 * Threads Domain: Thread Management Types
 * 
 * CRITICAL ARCHITECTURAL COMPLIANCE:
 * - Single source of truth for thread types
 * - Maximum file size: 300 lines
 * - Functions ≤8 lines each
 */

import { Message } from './messages';

// ============================================================================
// THREAD METADATA - Consolidated from all sources
// ============================================================================

export interface ThreadMetadata {
  // Core metadata (from registry)
  tags?: string[];
  priority?: number;
  category?: string | null;
  user_id?: string | null;
  custom_fields?: Record<string, string | number | boolean>;
  
  // Chat-store specific metadata
  optimization_results_count?: number;
  sub_agents_used?: string[];
  total_processing_time_ms?: number;
  user_rating?: number;
  bookmarked?: boolean;
  
  // Extended metadata for admin/special threads
  admin_type?: 'corpus' | 'synthetic' | 'users';
  title?: string;
  last_message?: string;
}

// ============================================================================
// THREAD INTERFACE - Unified Single Source of Truth
// ============================================================================

/**
 * Unified Thread interface - Single Source of Truth
 * 
 * BACKWARD COMPATIBILITY:
 * - Supports both 'name' (registry) and 'title' (chat-store) properties
 * - Includes all properties from both registry and chat-store versions
 * - Use getThreadTitle() helper for consistent title access
 * 
 * PROPERTY MAPPING:
 * - name/title: Both supported, title takes precedence if both exist
 * - status/is_active: Both supported, status takes precedence
 * - message_count: Optional for backward compatibility
 */
export interface Thread {
  // Core identifiers
  id: string;
  
  // Title/Name - Support both patterns for backward compatibility
  name?: string | null;
  title?: string;
  
  // Timestamps
  created_at: string;
  updated_at: string;
  
  // Content info
  message_count?: number;
  
  // Status - Support both patterns
  is_active?: boolean;
  status?: 'active' | 'archived' | 'deleted';
  
  // Messages
  last_message?: Message | null;
  last_message_preview?: string;
  
  // Relationships
  participants?: string[] | null;
  
  // Metadata
  metadata?: ThreadMetadata | null;
  
  // Direct tags for compatibility (also available in metadata)
  tags?: string[];
}

// ============================================================================
// THREAD STATE MANAGEMENT - Use canonical ThreadState from @shared/types/frontend_types
// ============================================================================
//
// NOTE: ThreadState moved to shared/types/frontend_types.ts for SSOT compliance
// Import ThreadState from there instead of defining locally

// ============================================================================
// THREAD UTILITY FUNCTIONS - Each function ≤8 lines
// ============================================================================

/**
 * Get thread title with fallback priority:
 * 1. thread.title (chat-store pattern)
 * 2. thread.name (registry pattern)
 * 3. thread.metadata?.title (metadata storage)
 * 4. thread.metadata?.last_message (preview)
 * 5. "New Chat" as default fallback
 */
export function getThreadTitle(thread: Thread): string {
  if (thread.title) return thread.title;
  if (thread.name) return thread.name;
  if (thread.metadata?.title) return thread.metadata.title;
  if (thread.metadata?.last_message) return thread.metadata.last_message;
  
  // Check if created_at is valid before using it for title generation
  if (thread.created_at) {
    const date = new Date(thread.created_at);
    // Check for valid date (not Unix epoch or invalid date)
    if (!isNaN(date.getTime()) && date.getTime() > 86400000) { // After Jan 2, 1970
      return `Chat ${date.toLocaleDateString()}`;
    }
  }
  
  return 'New Chat';
}

/**
 * Get thread status with fallback:
 * 1. thread.status (chat-store pattern)
 * 2. thread.is_active -> 'active'/'archived' (registry pattern)
 * 3. 'active' (default)
 */
export function getThreadStatus(thread: Thread): 'active' | 'archived' | 'deleted' {
  if (thread.status) return thread.status;
  if (thread.is_active === false) return 'archived';
  if (thread.is_active === true) return 'active';
  return 'active';
}

/**
 * Check if thread is active using either pattern
 */
export function isThreadActive(thread: Thread): boolean {
  if (thread.status) return thread.status === 'active';
  return thread.is_active !== false;
}

/**
 * Create Thread with dual property support for backward compatibility
 * Sets both name and title to the same value
 */
export function createThreadWithTitle(data: {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  [key: string]: unknown;
}): Thread {
  return {
    ...data,
    name: data.title,
    title: data.title,
  };
}

export function createThread(
  id: string,
  title: string,
  options: Partial<Thread> = {}
): Thread {
  const now = new Date().toISOString();
  return {
    id,
    title,
    name: title,
    created_at: options.created_at || now,
    updated_at: options.updated_at || now,
    ...options
  };
}

// ============================================================================
// THREAD VALIDATION - Each function ≤8 lines
// ============================================================================

export function isValidThread(obj: unknown): obj is Thread {
  if (typeof obj !== 'object' || obj === null) return false;
  const thread = obj as Thread;
  return (
    typeof thread.id === 'string' &&
    typeof thread.created_at === 'string' &&
    typeof thread.updated_at === 'string'
  );
}

export function hasMessages(thread: Thread): boolean {
  return Boolean(thread.message_count && thread.message_count > 0);
}

export function hasMetadata(thread: Thread): boolean {
  return Boolean(thread.metadata && Object.keys(thread.metadata).length > 0);
}

export function isBookmarked(thread: Thread): boolean {
  return Boolean(thread.metadata?.bookmarked);
}

export function hasParticipants(thread: Thread): boolean {
  return Boolean(thread.participants && thread.participants.length > 0);
}

export function hasTags(thread: Thread): boolean {
  const directTags = thread.tags && thread.tags.length > 0;
  const metadataTags = thread.metadata?.tags && thread.metadata.tags.length > 0;
  return Boolean(directTags || metadataTags);
}

// ============================================================================
// THREAD SORTING AND FILTERING - Each function ≤8 lines
// ============================================================================

export function sortThreadsByDate(threads: Thread[]): Thread[] {
  return [...threads].sort((a, b) => {
    const aTime = new Date(a.updated_at).getTime();
    const bTime = new Date(b.updated_at).getTime();
    return bTime - aTime;
  });
}

export function filterActiveThreads(threads: Thread[]): Thread[] {
  return threads.filter(isThreadActive);
}

export function filterThreadsByTag(threads: Thread[], tag: string): Thread[] {
  return threads.filter(thread => {
    const directTags = thread.tags || [];
    const metadataTags = thread.metadata?.tags || [];
    return [...directTags, ...metadataTags].includes(tag);
  });
}

export function searchThreads(threads: Thread[], query: string): Thread[] {
  const lowerQuery = query.toLowerCase();
  return threads.filter(thread => {
    const title = getThreadTitle(thread).toLowerCase();
    return title.includes(lowerQuery);
  });
}

// ============================================================================
// THREAD STATE HELPERS - Each function ≤8 lines
// ============================================================================

export function createThreadState(): ThreadState {
  return {
    threads: [],
    activeThreadId: null,
    currentThread: null,
    isLoading: false,
    error: null
  };
}

export function setActiveThread(
  state: ThreadState,
  threadId: string | null
): ThreadState {
  const currentThread = threadId 
    ? state.threads.find(t => t.id === threadId) || null
    : null;
  
  return {
    ...state,
    activeThreadId: threadId,
    currentThread
  };
}

// ============================================================================
// DEFAULT EXPORT FOR CONVENIENCE
// ============================================================================

export default {
  getThreadTitle,
  getThreadStatus,
  isThreadActive,
  createThreadWithTitle,
  createThread,
  isValidThread,
  sortThreadsByDate,
  filterActiveThreads,
  createThreadState,
  setActiveThread
};