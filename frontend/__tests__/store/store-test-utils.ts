/**
 * Store Test Utilities - Real Store Testing Helpers
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Developer Experience)
 * - Business Goal: Ensure store reliability across all tiers
 * - Value Impact: Prevents bugs that could lose revenue
 * - Revenue Impact: Critical for user auth and feature access
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { act, renderHook, RenderHookResult } from '@testing-library/react';
import { useAuthStore } from '@/store/authStore';
import { useChatStore } from '@/store/chat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useCorpusStore } from '@/store/corpusStore';
import { User } from '@/types/registry';
import type { Message } from '@/types/chat';

// Generic store hook type for type safety (≤8 lines)
type StoreHook<T> = () => T;
type StoreResult<T> = RenderHookResult<T, StoreHook<T>>;

// Mock localStorage for all store tests (≤8 lines)
export const createMockLocalStorage = () => ({
  getItem: jest.fn(),
  setItem: jest.fn(), 
  removeItem: jest.fn(),
  clear: jest.fn()
});

// Setup localStorage mock globally (≤8 lines)
export const setupMockLocalStorage = () => {
  const mockStorage = createMockLocalStorage();
  Object.defineProperty(window, 'localStorage', { value: mockStorage });
  return mockStorage;
};

// Auth Store Test Utilities
export namespace AuthStoreTestUtils {
  // Initialize auth store and return hook result (≤8 lines)
  export const initializeStore = (): StoreResult<ReturnType<typeof useAuthStore>> => {
    const result = renderHook(() => useAuthStore());
    act(() => result.current.reset());
    return result;
  };

  // Create mock user for different tiers (≤8 lines)
  export const createMockUser = (
    role: string, 
    permissions: string[] = []
  ): User & { role: string; permissions: string[] } => {
    return {
      id: `user-${role}`,
      email: `${role}@netra.ai`,
      full_name: `${role} User`,
      is_active: true,
      is_superuser: role === 'super_admin',
      role,
      permissions
    } as User & { role: string; permissions: string[] };
  };

  // Create test JWT token (≤8 lines)
  export const createTestToken = (suffix: string = 'default'): string => {
    return `jwt-token-${suffix}-${Date.now()}`;
  };

  // Perform login action and verify success (≤8 lines)
  export const performLogin = (
    result: StoreResult<ReturnType<typeof useAuthStore>>,
    user: User & { role: string; permissions: string[] },
    token: string
  ) => {
    act(() => result.current.login(user, token));
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(user);
  };

  // Verify permission checks (≤8 lines)
  export const verifyPermissions = (
    result: StoreResult<ReturnType<typeof useAuthStore>>,
    hasPermissions: string[],
    deniedPermissions: string[]
  ) => {
    hasPermissions.forEach(perm => 
      expect(result.current.hasPermission(perm)).toBe(true)
    );
    deniedPermissions.forEach(perm => 
      expect(result.current.hasPermission(perm)).toBe(false)
    );
  };

  // Verify role-based access (≤8 lines)
  export const verifyRoleAccess = (
    result: StoreResult<ReturnType<typeof useAuthStore>>,
    expectedDeveloper: boolean,
    expectedAdmin: boolean
  ) => {
    expect(result.current.isDeveloperOrHigher()).toBe(expectedDeveloper);
    expect(result.current.isAdminOrHigher()).toBe(expectedAdmin);
  };
}

// Chat Store Test Utilities  
export namespace ChatStoreTestUtils {
  // Initialize chat store and return hook result (≤8 lines)
  export const initializeStore = (): StoreResult<ReturnType<typeof useChatStore>> => {
    const result = renderHook(() => useChatStore());
    act(() => {
      result.current.clearMessages();
      result.current.setProcessing(false);
    });
    return result;
  };

  // Create mock message (≤8 lines)
  export const createMockMessage = (
    id: string,
    role: 'user' | 'assistant' = 'user',
    content: string = 'Test message'
  ): Message => ({
    id,
    role,
    content,
    timestamp: new Date().toISOString(),
    displayed_to_user: true
  });

  // Add message and verify (≤8 lines)
  export const addMessageAndVerify = (
    result: StoreResult<ReturnType<typeof useChatStore>>,
    message: Message
  ) => {
    act(() => result.current.addMessage(message));
    expect(result.current.messages).toContain(message);
  };

  // Verify message count (≤8 lines) 
  export const verifyMessageCount = (
    result: StoreResult<ReturnType<typeof useChatStore>>,
    expectedCount: number
  ) => {
    expect(result.current.messages).toHaveLength(expectedCount);
  };

  // Set processing state and verify (≤8 lines)
  export const setProcessingAndVerify = (
    result: StoreResult<ReturnType<typeof useChatStore>>,
    processing: boolean
  ) => {
    act(() => result.current.setProcessing(processing));
    expect(result.current.isProcessing).toBe(processing);
  };
}

// Unified Chat Store Test Utilities
export namespace UnifiedChatStoreTestUtils {
  // Initialize unified chat store (≤8 lines)
  export const initializeStore = (): StoreResult<ReturnType<typeof useUnifiedChatStore>> => {
    const result = renderHook(() => useUnifiedChatStore());
    act(() => result.current.resetLayers());
    return result;
  };

  // Update fast layer and verify (≤8 lines)
  export const updateFastLayerAndVerify = (
    result: StoreResult<ReturnType<typeof useUnifiedChatStore>>,
    data: Parameters<ReturnType<typeof useUnifiedChatStore>['updateFastLayer']>[0]
  ) => {
    act(() => result.current.updateFastLayer(data));
    expect(result.current.fastLayerData).toEqual(data);
  };

  // Update medium layer and verify (≤8 lines)
  export const updateMediumLayerAndVerify = (
    result: StoreResult<ReturnType<typeof useUnifiedChatStore>>,
    data: Parameters<ReturnType<typeof useUnifiedChatStore>['updateMediumLayer']>[0]
  ) => {
    act(() => result.current.updateMediumLayer(data));
    expect(result.current.mediumLayerData).toMatchObject(data);
  };

  // Set processing state and verify (≤8 lines)
  export const setProcessingAndVerify = (
    result: StoreResult<ReturnType<typeof useUnifiedChatStore>>,
    processing: boolean
  ) => {
    act(() => result.current.setProcessing(processing));
    expect(result.current.isProcessing).toBe(processing);
  };

  // Verify connection status (≤8 lines)
  export const verifyConnectionStatus = (
    result: StoreResult<ReturnType<typeof useUnifiedChatStore>>,
    connected: boolean,
    error?: string | null
  ) => {
    expect(result.current.isConnected).toBe(connected);
    if (error !== undefined) expect(result.current.connectionError).toBe(error);
  };
}

// Corpus Store Test Utilities
export namespace CorpusStoreTestUtils {
  // Initialize corpus store using renderHook pattern (≤8 lines)
  export const initializeStore = (): StoreResult<ReturnType<typeof useCorpusStore>> => {
    const result = renderHook(() => useCorpusStore());
    act(() => result.current.reset());
    return result;
  };

  // Create mock document (≤8 lines)
  export const createMockDocument = (
    id: string,
    corpusId: string,
    name: string = 'Test Document'
  ) => ({
    id,
    name,
    corpus_id: corpusId,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  });

  // Create mock corpus (≤8 lines)
  export const createMockCorpus = (
    id: string,
    name: string = 'Test Corpus'
  ) => ({
    id,
    name,
    description: 'Test Description',
    status: 'active' as const,
    created_by_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  });

  // Add document and verify (≤8 lines)
  export const addDocumentAndVerify = (
    result: StoreResult<ReturnType<typeof useCorpusStore>>,
    document: ReturnType<typeof createMockDocument>
  ) => {
    act(() => result.current.addDocument(document));
    expect(result.current.documents).toContain(document);
  };

  // Add corpus and verify (≤8 lines)
  export const addCorpusAndVerify = (
    result: StoreResult<ReturnType<typeof useCorpusStore>>,
    corpus: ReturnType<typeof createMockCorpus>
  ) => {
    act(() => result.current.addCorpus(corpus));
    expect(result.current.corpora).toContain(corpus);
  };
}

// Global test setup utilities
export namespace GlobalTestUtils {
  // Setup all required mocks for store tests (≤8 lines)
  export const setupStoreTestEnvironment = () => {
    const mockStorage = setupMockLocalStorage();
    global.fetch = jest.fn();
    global.WebSocket = jest.fn(() => ({
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: WebSocket.OPEN
    })) as any;
    return { mockStorage };
  };

  // Clean all mocks after tests (≤8 lines)
  export const cleanupStoreTestEnvironment = () => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
  };
}