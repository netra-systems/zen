/**
 * Shared mock setup for MessageInput component tests
 * Provides consistent mocking of all dependencies used by MessageInput
 */

import { jest } from '@jest/globals';

// Complete ThreadService mock with all required methods
export const mockThreadService = {
  listThreads: jest.fn().mockResolvedValue([]),
  createThread: jest.fn().mockResolvedValue({ 
    id: 'new-thread', 
    created_at: Math.floor(Date.now() / 1000), 
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 0,
    metadata: { title: 'New Chat', renamed: false }
  }),
  getThread: jest.fn().mockResolvedValue({
    id: 'test-thread',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 1,
    metadata: { title: 'Test Thread', renamed: false }
  }),
  deleteThread: jest.fn().mockResolvedValue(undefined),
  updateThread: jest.fn().mockResolvedValue({
    id: 'test-thread',
    created_at: Math.floor(Date.now() / 1000),
    updated_at: Math.floor(Date.now() / 1000),
    message_count: 1,
    metadata: { title: 'Updated Thread', renamed: true }
  }),
  getThreadMessages: jest.fn().mockResolvedValue({ 
    messages: [], 
    thread_id: 'test', 
    total: 0, 
    limit: 50, 
    offset: 0 
  })
};

export const mockThreadRenameService = {
  autoRenameThread: jest.fn().mockResolvedValue(undefined)
};

export const mockWebSocket = {
  sendMessage: jest.fn()
};

export const mockUnifiedChatStore = {
  setProcessing: jest.fn(),
  isProcessing: false,
  addMessage: jest.fn(),
  activeThreadId: 'thread-1',
  setActiveThread: jest.fn()
};

export const mockThreadStore = {
  currentThreadId: 'thread-1',
  setCurrentThread: jest.fn(),
  addThread: jest.fn()
};

export const mockAuthStore = {
  isAuthenticated: true
};

// Setup function to apply all mocks consistently
export const setupMessageInputMocks = () => {
  // Mock all the modules used by MessageInput
  jest.doMock('@/hooks/useWebSocket', () => ({
    useWebSocket: jest.fn(() => mockWebSocket)
  }));
  
  jest.doMock('@/store/unified-chat', () => ({
    useUnifiedChatStore: jest.fn(() => mockUnifiedChatStore)
  }));
  
  jest.doMock('@/store/threadStore', () => ({
    useThreadStore: jest.fn(() => mockThreadStore)
  }));
  
  jest.doMock('@/store/authStore', () => ({
    useAuthStore: jest.fn(() => mockAuthStore)
  }));
  
  jest.doMock('@/services/threadService', () => ({
    ThreadService: mockThreadService
  }));
  
  jest.doMock('@/services/threadRenameService', () => ({
    ThreadRenameService: mockThreadRenameService
  }));
  
  jest.doMock('@/lib/utils', () => ({
    generateUniqueId: jest.fn((prefix: string) => `${prefix}-${Date.now()}`),
    cn: jest.fn((...classes: any[]) => classes.filter(Boolean).join(' '))
  }));
};

// Reset function to clear all mocks
export const resetMessageInputMocks = () => {
  Object.values(mockThreadService).forEach(mock => (mock as jest.Mock).mockClear());
  Object.values(mockThreadRenameService).forEach(mock => (mock as jest.Mock).mockClear());
  Object.values(mockWebSocket).forEach(mock => (mock as jest.Mock).mockClear());
  Object.values(mockUnifiedChatStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
  Object.values(mockThreadStore).forEach(mock => 
    typeof mock === 'function' && (mock as jest.Mock).mockClear?.()
  );
};

// Helper to override specific mock values for individual tests
export const overrideMocks = (overrides: {
  threadService?: Partial<typeof mockThreadService>;
  unifiedChatStore?: Partial<typeof mockUnifiedChatStore>;
  threadStore?: Partial<typeof mockThreadStore>;
  authStore?: Partial<typeof mockAuthStore>;
  webSocket?: Partial<typeof mockWebSocket>;
}) => {
  if (overrides.threadService) {
    Object.assign(mockThreadService, overrides.threadService);
  }
  if (overrides.unifiedChatStore) {
    Object.assign(mockUnifiedChatStore, overrides.unifiedChatStore);
  }
  if (overrides.threadStore) {
    Object.assign(mockThreadStore, overrides.threadStore);
  }
  if (overrides.authStore) {
    Object.assign(mockAuthStore, overrides.authStore);
  }
  if (overrides.webSocket) {
    Object.assign(mockWebSocket, overrides.webSocket);
  }
};