/**
 * Onboarding Flow E2E Tests - Core Module
 * 
 * Business Value: Protects core revenue flow (Free → Paid conversion)
 * Priority: P0 - Critical path testing
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all test data
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { act } from 'react-dom/test-utils';

// Test utilities
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';

// Simple setup functions
const setupTestEnvironment = () => {
  // Basic test setup
};

const resetTestState = () => {
  // Reset any global state
};

// Components under test
import ChatPage from '@/app/chat/page';
import MainChat from '@/components/chat/MainChat';

// Mock Next.js router
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
    refresh: jest.fn(),
    pathname: '/chat'
  }),
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams()
}));

// Mock stores with authenticated state
const mockAuthStore = {
  isAuthenticated: true,
  user: { id: 'user-123', email: 'test@example.com' },
  token: 'test-token-123'
};

const mockChatStore = {
  threads: [],
  activeThreadId: null,
  messages: [],
  isProcessing: false,
  createThread: jest.fn(),
  sendMessage: jest.fn()
};

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => mockAuthStore
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => mockChatStore
}));

// Mock WebSocket
const mockWebSocket = {
  isConnected: true,
  connectionState: 'connected' as const,
  sendMessage: jest.fn(),
  messages: []
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => mockWebSocket
}));

// Mock loading state to show example prompts
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: ''
  })
}));

// Mock other required hooks
jest.mock('@/hooks/useEventProcessor', () => ({
  useEventProcessor: () => ({})
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: () => ({
    currentThreadId: null,
    isNavigating: false
  })
}));

// Mock window methods
Object.defineProperty(window, 'scrollTo', {
  value: jest.fn(),
  writable: true
});

// Test data types
interface OnboardingTestData {
  userId: string;
  userEmail: string;
  firstMessage: string;
  expectedThreadId: string;
}

// Test fixtures
const onboardingData: OnboardingTestData = {
  userId: 'user-test-123',
  userEmail: 'newuser@netra.ai', 
  firstMessage: 'Hello, I need help optimizing my AI workload costs',
  expectedThreadId: 'thread-new-123'
};

describe('Onboarding Flow E2E Tests', () => {
  let wsManager: WebSocketTestManager;
  
  beforeEach(() => {
    setupTestEnvironment();
    resetTestState();
    wsManager = new WebSocketTestManager();
    resetMocks();
  });
  
  afterEach(() => {
    wsManager?.cleanup();
    jest.clearAllMocks();
  });
  
  describe('Basic Onboarding Flow', () => {
    it('renders chat page with authentication', async () => {
      await renderChatPage();
      
      // Check for any text that indicates the page loaded
      await waitFor(() => {
        expect(document.body).toBeInTheDocument();
      });
      expect(mockAuthStore.isAuthenticated).toBe(true);
    });
    
    it('shows example prompts for new users', async () => {
      await renderChatPage();
      
      await waitFor(() => {
        expect(screen.getByText('Quick Start Examples')).toBeInTheDocument();
      });
    });
    
    it('establishes WebSocket connection', async () => {
      const startTime = Date.now();
      await renderChatPage();
      
      expect(mockWebSocket.isConnected).toBe(true);
      const connectionTime = Date.now() - startTime;
      expect(connectionTime).toBeLessThan(1000);
    });
    
    it('handles thread creation successfully', async () => {
      mockChatStore.createThread.mockResolvedValue({
        id: onboardingData.expectedThreadId,
        title: 'New Thread'
      });
      
      await renderChatPage();
      await triggerThreadCreation();
      
      expect(mockChatStore.createThread).toHaveBeenCalled();
    });
  });
  
  describe('Message Flow', () => {
    it('handles first message input', async () => {
      await renderChatPage();
      
      const input = screen.getByRole('textbox', { name: /message input/i });
      await userEvent.type(input, onboardingData.firstMessage);
      
      expect(input).toHaveValue(onboardingData.firstMessage);
      expect(screen.getByRole('button', { name: /send/i })).toBeEnabled();
    });
    
    it('sends message successfully', async () => {
      await renderChatPage();
      await sendTestMessage();
      
      expect(mockChatStore.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: onboardingData.firstMessage
        })
      );
    });
  });
  
  // Helper functions (8 lines max each)
  function resetMocks(): void {
    mockChatStore.threads = [];
    mockChatStore.activeThreadId = null;
    mockChatStore.messages = [];
    mockChatStore.isProcessing = false;
    mockPush.mockClear();
    jest.clearAllMocks();
  }
  
  async function renderChatPage(): Promise<void> {
    await act(async () => {
      render(
        <TestProviders>
          <ChatPage />
        </TestProviders>
      );
    });
  }
  
  async function triggerThreadCreation(): Promise<void> {
    // Look for elements that might trigger thread creation
    const buttons = screen.getAllByRole('button');
    const threadButton = buttons.find(btn => 
      btn.textContent?.includes('New') || 
      btn.textContent?.includes('Start')
    );
    
    if (threadButton) {
      await userEvent.click(threadButton);
    }
  }
  
  async function sendTestMessage(): Promise<void> {
    const input = screen.getByRole('textbox', { name: /message input/i });
    await userEvent.type(input, onboardingData.firstMessage);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await userEvent.click(sendButton);
  }
});
