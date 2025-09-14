/**
 * Thread Test Helpers - Comprehensive Thread Testing Utilities
 * 
 * BUSINESS VALUE JUSTIFICATION:
 * - Segment: All (Free → Enterprise)
 * - Business Goal: Ensure thread management reliability for user experience
 * - Value Impact: Prevents thread corruption and navigation issues
 * - Revenue Impact: Protects user retention and $150K+ MRR from thread-dependent workflows
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 * - TypeScript with full type safety
 * - Composable and reusable utilities
 */

import { jest } from '@jest/globals';
import { createMockMessage, MockMessage, MockThread } from './test-helpers';
import { ThreadState } from '@shared/types/frontend_types';

// Define types locally to avoid import issues during testing
export interface ThreadMetadata {
  tags?: string[];
  priority?: number;
  category?: string | null;
  user_id?: string | null;
  custom_fields?: Record<string, string | number | boolean>;
  optimization_results_count?: number;
  sub_agents_used?: string[];
  total_processing_time_ms?: number;
  user_rating?: number;
  bookmarked?: boolean;
  admin_type?: 'corpus' | 'synthetic' | 'users';
  title?: string;
  last_message?: string;
}

export interface Thread {
  id: string;
  name?: string | null;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  is_active?: boolean;
  status?: 'active' | 'archived' | 'deleted';
  metadata?: ThreadMetadata | null;
  tags?: string[];
}

// ThreadState imported from canonical SSOT location: @shared/types/frontend_types

// ============================================================================
// THREAD MOCK FACTORIES - Thread generation utilities
// ============================================================================

// MockThread type imported from test-helpers.tsx

/**
 * Create mock thread with minimal data
 */
export function createMockThread(overrides: Partial<MockThread> = {}): MockThread {
  const id = overrides.id || `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const title = overrides.title || `Test Thread ${id.slice(-8)}`;
  
  return {
    id,
    title,
    name: title, // Support both title and name for compatibility
    user_id: overrides.user_id || `user_${Date.now()}`,
    created_at: overrides.created_at || new Date().toISOString(),
    updated_at: overrides.updated_at || new Date().toISOString(),
    message_count: overrides.message_count || 0,
    is_active: overrides.is_active !== false,
    status: overrides.status || 'active',
    ...overrides
  };
}

/**
 * Create active thread with messages
 */
export function createActiveThread(messageCount: number = 5): MockThread {
  return createMockThread({
    message_count: messageCount,
    is_active: true,
    status: 'active',
    updated_at: new Date().toISOString()
  });
}

/**
 * Create archived thread
 */
export function createArchivedThread(): MockThread {
  return createMockThread({
    is_active: false,
    status: 'archived',
    updated_at: new Date(Date.now() - 86400000).toISOString() // 1 day ago
  });
}

/**
 * Create thread with metadata
 */
export function createThreadWithMetadata(metadata: Partial<ThreadMetadata> = {}): MockThread {
  return createMockThread({
    metadata: {
      tags: ['test'],
      priority: 1,
      bookmarked: false,
      ...metadata
    }
  });
}

/**
 * Create list of mock threads
 */
export function createMockThreadList(count: number = 3): MockThread[] {
  return Array.from({ length: count }, (_, i) =>
    createMockThread({
      title: `Thread ${i + 1}`,
      message_count: Math.floor(Math.random() * 20),
      created_at: new Date(Date.now() - i * 3600000).toISOString() // Stagger by hours
    })
  );
}

// ============================================================================
// THREAD STATE HELPERS - State management utilities
// ============================================================================

/**
 * Create mock thread state
 */
export function createMockThreadState(overrides: Partial<ThreadState> = {}): ThreadState {
  return {
    threads: [],
    activeThreadId: null,
    currentThread: null,
    isLoading: false,
    error: null,
    ...overrides
  };
}

/**
 * Create thread state with active thread
 */
export function createThreadStateWithActive(activeThread: MockThread): ThreadState {
  return createMockThreadState({
    threads: [activeThread],
    activeThreadId: activeThread.id,
    currentThread: activeThread
  });
}

/**
 * Create thread state with multiple threads
 */
export function createThreadStateWithThreads(threads: MockThread[]): ThreadState {
  return createMockThreadState({
    threads,
    activeThreadId: threads[0]?.id || null,
    currentThread: threads[0] || null
  });
}

/**
 * Update thread state with new thread
 */
export function addThreadToState(state: ThreadState, thread: MockThread): ThreadState {
  return {
    ...state,
    threads: [...state.threads, thread]
  };
}

// ============================================================================
// THREAD NAVIGATION HELPERS - Navigation testing utilities
// ============================================================================

/**
 * Mock thread navigation functions
 */
export function setupThreadNavigationMocks() {
  return {
    selectThread: jest.fn(),
    createThread: jest.fn(() => Promise.resolve(createMockThread())),
    archiveThread: jest.fn(() => Promise.resolve({ success: true })),
    deleteThread: jest.fn(() => Promise.resolve({ success: true }))
  };
}

/**
 * Simulate thread selection
 */
export function simulateThreadSelection(threadId: string): {
  currentThreadId: string;
  previousThreadId: string | null;
} {
  return {
    currentThreadId: threadId,
    previousThreadId: null
  };
}

/**
 * Mock thread router navigation
 */
export function createMockThreadRouter() {
  return {
    push: jest.fn(),
    replace: jest.fn(),
    navigateToThread: jest.fn((threadId: string) => `/chat/${threadId}`)
  };
}

// ============================================================================
// THREAD VALIDATION HELPERS - Testing utilities
// ============================================================================

/**
 * Assert thread has required fields
 */
export function expectValidThread(thread: any): void {
  expect(thread).toBeDefined();
  expect(typeof thread.id).toBe('string');
  expect(typeof thread.title === 'string' || typeof thread.name === 'string').toBe(true);
  expect(typeof thread.created_at).toBe('string');
}

/**
 * Assert thread is active
 */
export function expectThreadActive(thread: MockThread): void {
  expect(thread.is_active !== false).toBe(true);
  expect(thread.status !== 'archived').toBe(true);
  expect(thread.status !== 'deleted').toBe(true);
}

/**
 * Assert thread has messages
 */
export function expectThreadHasMessages(thread: MockThread): void {
  expect(thread.message_count).toBeGreaterThan(0);
}

/**
 * Assert thread belongs to user
 */
export function expectThreadBelongsToUser(thread: MockThread, userId: string): void {
  expect(thread.user_id).toBe(userId);
}

// ============================================================================
// THREAD SEARCH AND FILTER HELPERS - Query testing utilities
// ============================================================================

/**
 * Filter threads by status
 */
export function filterThreadsByStatus(
  threads: MockThread[],
  status: 'active' | 'archived' | 'deleted'
): MockThread[] {
  return threads.filter(thread => {
    if (thread.status) return thread.status === status;
    if (status === 'active') return thread.is_active !== false;
    if (status === 'archived') return thread.is_active === false;
    return false;
  });
}

/**
 * Search threads by title
 */
export function searchThreadsByTitle(threads: MockThread[], query: string): MockThread[] {
  const lowerQuery = query.toLowerCase();
  return threads.filter(thread => {
    const title = thread.title || thread.name || '';
    return title.toLowerCase().includes(lowerQuery);
  });
}

/**
 * Sort threads by date
 */
export function sortThreadsByDate(threads: MockThread[], newest: boolean = true): MockThread[] {
  return [...threads].sort((a, b) => {
    const aTime = new Date(a.updated_at).getTime();
    const bTime = new Date(b.updated_at).getTime();
    return newest ? bTime - aTime : aTime - bTime;
  });
}

/**
 * Get threads with messages
 */
export function getThreadsWithMessages(threads: MockThread[]): MockThread[] {
  return threads.filter(thread => thread.message_count > 0);
}

// ============================================================================
// THREAD-MESSAGE INTEGRATION HELPERS - Combined utilities
// ============================================================================

/**
 * Create thread with associated messages
 */
export function createThreadWithMessages(
  messageCount: number = 3,
  threadOverrides: Partial<MockThread> = {}
): { thread: MockThread; messages: MockMessage[] } {
  const thread = createMockThread({
    message_count: messageCount,
    ...threadOverrides
  });
  
  const messages = Array.from({ length: messageCount }, (_, i) =>
    createMockMessage({
      thread_id: thread.id,
      content: `Message ${i + 1} in ${thread.title}`,
      role: i % 2 === 0 ? 'user' : 'assistant',
      created_at: new Date(Date.now() + i * 1000).toISOString()
    })
  );
  
  return { thread, messages };
}

/**
 * Create conversation flow for testing
 */
export function createConversationFlow(turns: number = 3): {
  thread: MockThread;
  messages: MockMessage[];
} {
  const thread = createMockThread({
    title: 'Test Conversation',
    message_count: turns * 2
  });
  
  const messages: MockMessage[] = [];
  for (let i = 0; i < turns; i++) {
    messages.push(
      createMockMessage({
        thread_id: thread.id,
        role: 'user',
        content: `User question ${i + 1}`,
        created_at: new Date(Date.now() + i * 2000).toISOString()
      }),
      createMockMessage({
        thread_id: thread.id,
        role: 'assistant',
        content: `Assistant response ${i + 1}`,
        created_at: new Date(Date.now() + i * 2000 + 1000).toISOString()
      })
    );
  }
  
  return { thread, messages };
}

// All functions are already exported above - no need for re-export