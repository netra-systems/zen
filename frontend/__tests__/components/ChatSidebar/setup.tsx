/**
 * ChatSidebar Test Setup and Utilities
 * Shared setup, mocks, and utilities for ChatSidebar component tests
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';

import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import * as ThreadServiceModule from '@/services/threadService';
import { TestProviders } from '../../test-utils/providers';

// Mock dependencies
jest.mock('@/store/unified-chat');
jest.mock('@/store/authStore');
jest.mock('@/services/threadService');
jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, variant, size, disabled }: any) => (
    <button onClick={onClick} data-variant={variant} data-size={size} disabled={disabled}>
      {children}
    </button>
  )
}));
jest.mock('@/components/ui/input', () => ({
  Input: ({ value, onChange, placeholder, ...props }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...props}
    />
  )
}));

export const mockChatStore = {
  isProcessing: false,
  activeThreadId: 'thread-123',
  setActiveThread: jest.fn(),
  clearMessages: jest.fn(),
  resetLayers: jest.fn(),
  threads: [] as any[],
  currentThreadId: null as string | null,
};

export const mockAuthStore = {
  isDeveloperOrHigher: jest.fn(() => false)
};

export const mockThreadService = {
  listThreads: jest.fn().mockResolvedValue([]),
  createThread: jest.fn().mockResolvedValue({ 
    id: 'new-thread', 
    created_at: Date.now(), 
    updated_at: Date.now() 
  }),
  getThread: jest.fn(),
  deleteThread: jest.fn(),
  updateThread: jest.fn()
};

// Sample thread data
export const sampleThreads = [
  {
    id: 'thread-1',
    title: 'AI Optimization Discussion',
    lastMessage: 'How can I optimize my model?',
    lastActivity: new Date().toISOString(),
    messageCount: 15,
    isActive: false,
    participants: ['user1', 'assistant'],
    tags: ['optimization', 'ai']
  },
  {
    id: 'thread-2', 
    title: 'Performance Analysis',
    lastMessage: 'The results show 20% improvement',
    lastActivity: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    messageCount: 8,
    isActive: true,
    participants: ['user1', 'assistant'],
    tags: ['performance']
  },
  {
    id: 'thread-3',
    title: 'Data Processing Pipeline',
    lastMessage: 'Pipeline completed successfully',
    lastActivity: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
    messageCount: 32,
    isActive: false,
    participants: ['user1', 'assistant'],
    tags: ['data', 'pipeline']
  }
];

export class ChatSidebarTestSetup {
  beforeEach() {
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });

    jest.clearAllMocks();
    (useUnifiedChatStore as jest.Mock).mockReturnValue(mockChatStore);
    (useAuthStore as jest.Mock).mockReturnValue(mockAuthStore);
    // Mock ThreadService
    (ThreadServiceModule.ThreadService as any) = mockThreadService;
  }

  afterEach() {
    jest.restoreAllMocks();
  }

  // Configure store with custom data
  configureStore(overrides: Partial<typeof mockChatStore>) {
    const storeConfig = { ...mockChatStore, ...overrides };
    (useUnifiedChatStore as jest.Mock).mockReturnValue(storeConfig);
    return storeConfig;
  }

  // Configure auth store
  configureAuth(overrides: Partial<typeof mockAuthStore>) {
    const authConfig = { ...mockAuthStore, ...overrides };
    (useAuthStore as jest.Mock).mockReturnValue(authConfig);
    return authConfig;
  }

  // Configure thread service responses
  configureThreadService(overrides: Partial<typeof mockThreadService>) {
    const serviceConfig = { ...mockThreadService, ...overrides };
    (ThreadServiceModule.ThreadService as any) = serviceConfig;
    return serviceConfig;
  }

  // Helper to create test threads
  createThread(overrides: Partial<typeof sampleThreads[0]> = {}) {
    return {
      id: `thread-${Math.random().toString(36).substr(2, 9)}`,
      title: 'Test Thread',
      lastMessage: 'Test message',
      lastActivity: new Date().toISOString(),
      messageCount: 1,
      isActive: false,
      participants: ['user1', 'assistant'],
      tags: ['test'],
      ...overrides
    };
  }

  // Mock loading state
  mockLoadingState() {
    this.configureStore({ 
      isProcessing: true,
      threads: []
    });
  }

  // Mock error state
  mockErrorState(error: string = 'Test error') {
    this.configureStore({ 
      error: error,
      threads: []
    });
  }
}

export const createTestSetup = () => new ChatSidebarTestSetup();

// Render helper with providers
export const renderWithProvider = (component: React.ReactElement) => {
  return render(
    <TestProviders>
      {component}
    </TestProviders>
  );
};

// Test utilities
export const findThreadElement = (container: HTMLElement, threadId: string) => {
  return container.querySelector(`[data-testid="thread-item-${threadId}"]`);
};

export const findThreadByTitle = (container: HTMLElement, title: string) => {
  return Array.from(container.querySelectorAll('[data-testid*="thread-item"]')).find(
    el => el.textContent?.includes(title)
  ) as HTMLElement;
};

// Mock user interactions
export const mockUserInteraction = {
  clickThread: (element: HTMLElement) => {
    element.click();
  },
  
  hoverThread: (element: HTMLElement) => {
    element.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  },
  
  contextMenu: (element: HTMLElement) => {
    element.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true }));
  }
};

// Time formatting utility
export const formatRelativeTime = (date: string | Date) => {
  const now = new Date();
  const target = new Date(date);
  const diffInMs = now.getTime() - target.getTime();
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
  const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  } else if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  } else {
    return `${diffInDays}d ago`;
  }
};

// Export mocks for use in tests
export { useUnifiedChatStore, useAuthStore, ThreadServiceModule };