/**
 * Component Mocks Setup for Jest Tests
 * ===================================
 * 
 * Sets up comprehensive mocks for components that tests expect.
 * This ensures tests can find the proper test IDs and functionality.
 */

import {
  MessageList,
  MessageItem,
  FormattedMessageContent,
  MainChat,
  ChatSidebar,
  MessageInput,
  ConnectionStatusIndicator,
  ErrorBoundary,
  ThinkingIndicator,
} from '../__mocks__/comprehensive-component-mocks';

// Mock the actual component modules
jest.mock('@/components/chat/MainChat', () => ({
  MainChat
}));

jest.mock('@/components/chat/MessageInput', () => ({
  MessageInput
}));

jest.mock('@/components/chat/MessageList', () => ({
  MessageList
}));

jest.mock('@/components/chat/MessageItem', () => ({
  MessageItem
}));

jest.mock('@/components/chat/ChatSidebar', () => ({
  ChatSidebar
}));

jest.mock('@/components/chat/FormattedMessageContent', () => ({
  FormattedMessageContent
}));

jest.mock('@/components/chat/ConnectionStatusIndicator', () => ({
  ConnectionStatusIndicator
}));

jest.mock('@/components/chat/ErrorBoundary', () => ({
  ErrorBoundary
}));

jest.mock('@/components/chat/ThinkingIndicator', () => ({
  ThinkingIndicator
}));

// Mock UI components that might be missing
jest.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children, ...props }: any) => (
    <div data-testid="scroll-area" {...props}>
      {children}
    </div>
  )
}));

// Mock loading components
jest.mock('@/components/loading/MessageSkeleton', () => ({
  MessageSkeleton: ({ type, ...props }: any) => (
    <div data-testid="message-skeleton" data-type={type} {...props}>
      Loading...
    </div>
  ),
  SkeletonPresets: {}
}));

// Mock hooks that components depend on
jest.mock('@/hooks/useProgressiveLoading', () => ({
  useProgressiveLoading: jest.fn(() => ({
    shouldShowSkeleton: false,
    shouldShowContent: true,
    contentOpacity: 1,
    startLoading: jest.fn(),
    completeLoading: jest.fn()
  }))
}));

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock Zustand stores with default values
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => {
    const store = (global as any).mockStore || {};
    return {
      messages: [],
      isProcessing: false,
      isThreadLoading: false,
      currentRunId: null,
      activeThreadId: 'thread-1',
      threads: [],
      ...store
    };
  })
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => {
    const authState = (global as any).mockAuthState || {};
    return {
      isAuthenticated: true,
      user: { id: 'test-user', email: 'test@example.com', name: 'Test User' },
      token: 'test-token',
      loading: false,
      error: null,
      ...authState
    };
  })
}));

jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({
    currentThreadId: 'thread-1',
    threads: [],
    setCurrentThread: jest.fn(),
    addThread: jest.fn()
  }))
}));

// Initialize global mock state
if (!(global as any).mockStore) {
  (global as any).mockStore = {
    messages: [],
    threads: [],
    isProcessing: false,
    isThreadLoading: false,
    activeThreadId: 'thread-1',
    sendMessage: jest.fn(),
    addMessage: jest.fn(),
    updateMessage: jest.fn(),
    deleteMessage: jest.fn(),
    createThread: jest.fn(),
    addThread: jest.fn(),
    setActiveThread: jest.fn(),
    deleteThread: jest.fn()
  };
}

if (!(global as any).mockAuthState) {
  (global as any).mockAuthState = {
    user: {
      id: 'test-user',
      email: 'test@example.com',
      full_name: 'Test User'
    },
    loading: false,
    error: null,
    authConfig: {
      development_mode: true,
      google_client_id: 'mock-google-client-id',
      endpoints: {
        login: 'http://localhost:8081/auth/login',
        logout: 'http://localhost:8081/auth/logout',
        callback: 'http://localhost:8081/auth/callback',
        token: 'http://localhost:8081/auth/token',
        user: 'http://localhost:8081/auth/me',
        dev_login: 'http://localhost:8081/auth/dev/login'
      }
    },
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.test-signature',
    isAuthenticated: true,
    initialized: true
  };
}

// Export for use in tests
export { MessageList, MessageItem, FormattedMessageContent, MainChat, ChatSidebar, MessageInput, ConnectionStatusIndicator, ErrorBoundary, ThinkingIndicator };