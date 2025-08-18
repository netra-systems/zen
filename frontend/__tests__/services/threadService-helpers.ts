/**
 * Thread Service Test Helpers
 * ARCHITECTURAL COMPLIANCE: Modular test utilities ≤300 lines
 * Each function ≤8 lines for maintainability
 */

import { Thread, ThreadMetadata } from '@/types/registry';
import { ThreadMessage, ThreadMessagesResponse } from '@/services/threadService';

// ============================================================================
// MOCK DATA FACTORIES
// ============================================================================

export function createMockThread(id: string, title: string): Thread {
  return {
    id,
    title,
    name: title,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    is_active: true
  };
}

export function createMockThreads(count: number): Thread[] {
  return Array.from({ length: count }, (_, i) => 
    createMockThread(`thread-${i + 1}`, `Chat ${i + 1}`)
  );
}

export function createMockMessage(id: string, content: string): ThreadMessage {
  return {
    id,
    role: 'user',
    content,
    created_at: Date.now()
  };
}

export function createMockMessagesResponse(threadId: string, count: number): ThreadMessagesResponse {
  const messages = Array.from({ length: count }, (_, i) => 
    createMockMessage(`msg-${i + 1}`, `Message ${i + 1}`)
  );
  return {
    thread_id: threadId,
    messages,
    total: count,
    limit: 50,
    offset: 0
  };
}

export function createApiError(status: number, message: string): Error {
  const error = new Error(message) as any;
  error.status = status;
  error.response = { status, data: { detail: message } };
  return error;
}

// ============================================================================
// API CALL EXPECTATIONS
// ============================================================================

export function expectListCall(mockApiClient: any, limit: number, offset: number): void {
  expect(mockApiClient.get).toHaveBeenCalledWith('/api/threads', {
    params: { limit, offset }
  });
}

export function expectGetCall(mockApiClient: any, threadId: string): void {
  expect(mockApiClient.get).toHaveBeenCalledWith(`/api/threads/${threadId}`);
}

export function expectCreateCall(mockApiClient: any, data: any): void {
  expect(mockApiClient.post).toHaveBeenCalledWith('/api/threads', data);
}

export function expectUpdateCall(mockApiClient: any, threadId: string, data: any): void {
  expect(mockApiClient.put).toHaveBeenCalledWith(`/api/threads/${threadId}`, data);
}

export function expectDeleteCall(mockApiClient: any, threadId: string): void {
  expect(mockApiClient.delete).toHaveBeenCalledWith(`/api/threads/${threadId}`);
}

export function expectMessagesCall(mockApiClient: any, threadId: string, limit: number, offset: number): void {
  expect(mockApiClient.get).toHaveBeenCalledWith(
    `/api/threads/${threadId}/messages`,
    { params: { limit, offset } }
  );
}

// ============================================================================
// RESULT VALIDATORS
// ============================================================================

export function expectMixedConcurrentResults(results: PromiseSettledResult<any>[]): void {
  expect(results).toHaveLength(3);
  const fulfilled = results.filter(r => r.status === 'fulfilled').length;
  const rejected = results.filter(r => r.status === 'rejected').length;
  expect(fulfilled).toBeGreaterThan(0);
  expect(rejected).toBeGreaterThan(0);
}

// ============================================================================
// TEST DATA PRESETS
// ============================================================================

export const TEST_METADATA: ThreadMetadata = {
  tags: ['important'],
  priority: 1,
  bookmarked: true
};

export const URGENT_METADATA: ThreadMetadata = {
  priority: 5,
  tags: ['urgent'],
  category: 'high-priority'
};

export const EMPTY_METADATA: ThreadMetadata = {};