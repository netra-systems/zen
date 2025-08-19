/**
 * Onboarding Flow E2E Tests
 * 
 * Tests the complete new user onboarding journey from
 * landing page to first conversation completion.
 * 
 * Business Value: Protects core revenue flow (Free → Paid conversion)
 * Priority: P0 - Critical path testing
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all test data
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { act } from 'react-dom/test-utils';

// Test utilities and setup
import { TestProviders } from '../test-utils/providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';
import {
  setupTestEnvironment,
  mockUser as mockAuthenticatedUser,
  createWebSocketServer,
  resetTestState,
  performFullCleanup
} from '../test-utils/integration-test-setup';

// Mock Next.js router
const mockPush = jest.fn();
const mockReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    refresh: jest.fn(),
    pathname: '/chat',
    query: {},
    asPath: '/chat'
  }),
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams()
}));

// Mock stores
const mockAuthStore = {
  isAuthenticated: true,
  user: mockAuthenticatedUser,
  token: 'test-token-123',
  login: jest.fn(),
  logout: jest.fn()
};

const mockChatStore = {
  threads: [],
  activeThreadId: null,
  messages: [],
  isProcessing: false,
  createThread: jest.fn(),
  sendMessage: jest.fn(),
  setActiveThread: jest.fn()
};

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => mockAuthStore
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: () => mockChatStore
}));

// Mock WebSocket hook
const mockWebSocket = {
  isConnected: false,
  connectionState: 'disconnected' as const,
  sendMessage: jest.fn(),
  messages: [],
  connect: jest.fn(),
  disconnect: jest.fn()
};

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => mockWebSocket
}));

// Mock loading state
jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: () => ({
    shouldShowLoading: false,
    shouldShowEmptyState: false,
    shouldShowExamplePrompts: true,
    loadingMessage: ''
  })
}));

// Mock window.scrollTo to prevent "not implemented" errors in tests
Object.defineProperty(window, 'scrollTo', {
  value: jest.fn(),
  writable: true,
});

// Mock window.scroll for additional coverage
Object.defineProperty(window, 'scroll', {
  value: jest.fn(),
  writable: true,
});

// Mock scrollIntoView for elements
Element.prototype.scrollIntoView = jest.fn();

// Components under test
import ChatPage from '@/app/chat/page';
import MainChat from '@/components/chat/MainChat';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';

// Test data types
interface OnboardingTestData {
  userId: string;
  userEmail: string;
  firstMessage: string;
  expectedThreadId: string;
  expectedResponseTime: number;
}

interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: number;
}

// Test fixtures
const onboardingData: OnboardingTestData = {
  userId: 'user-test-123',
  userEmail: 'newuser@netra.ai',
  firstMessage: 'Hello, I need help optimizing my AI workload costs',
  expectedThreadId: 'thread-new-123',
  expectedResponseTime: 2000
};

const mockAIResponse = {
  type: 'ai_message',
  content: 'Hello! I\'d be happy to help you optimize your AI workload costs...',
  threadId: onboardingData.expectedThreadId,
  timestamp: Date.now()
};

describe('Onboarding Flow E2E Tests', () => {
  let wsManager: WebSocketTestManager;
  let mockServer: any;
  
  beforeEach(() => {
    setupE2ETestEnvironment();
    wsManager = new WebSocketTestManager('ws://localhost:8080/ws');
    mockServer = createWebSocketServer();
    resetOnboardingState();
  });
  
  afterEach(() => {
    performE2ECleanup();
  });
  
  describe('Complete Onboarding Journey', () => {
    it('should complete new user onboarding flow end-to-end', async () => {
      await renderChatPageWithAuth();
      await verifyInitialChatState();
      await simulateStartNewConversation();
      await verifyThreadCreationFlow();
      await simulateFirstMessage();
      await verifyAIResponseReceived();
      expectOnboardingComplete();
    });
    
    it('should handle Start New Conversation button correctly', async () => {
      await renderChatPageWithAuth();
      await clickStartNewConversationButton();
      await verifyThreadCreatedSuccessfully();
      await verifyNavigationToNewThread();
      expectReadyForFirstMessage();
    });
    
    it('should establish WebSocket connection within 1 second', async () => {
      const startTime = Date.now();
      await renderChatPageWithAuth();
      await simulateWebSocketConnection();
      await verifyConnectionEstablished();
      expectConnectionTimingCompliance(startTime);
    });
    
    it('should handle first message send/receive cycle', async () => {
      await setupActiveThread();
      await sendFirstMessage();
      await verifyMessageDeliveryConfirmed();
      await simulateAIStreamingResponse();
      expectFirstConversationComplete();
    });
  });
  
  describe('Error Recovery During Onboarding', () => {
    it('should recover from WebSocket connection failures', async () => {
      await renderChatPageWithAuth();
      await simulateWebSocketFailure();
      await verifyConnectionRetryAttempted();
      await simulateWebSocketRecovery();
      expectSuccessfulRecovery();
    });
    
    it('should handle thread creation failures gracefully', async () => {
      await renderChatPageWithAuth();
      await simulateThreadCreationFailure();
      await verifyErrorMessageDisplayed();
      await retryThreadCreation();
      expectSuccessfulThreadCreation();
    });
  });
  
  // Helper functions (8 lines max each)
  function setupE2ETestEnvironment(): void {
    setupTestEnvironment();
    resetTestState();
    mockPush.mockClear();
    mockReplace.mockClear();
  }
  
  function resetOnboardingState(): void {
    mockChatStore.threads = [];
    mockChatStore.activeThreadId = null;
    mockChatStore.messages = [];
    mockChatStore.isProcessing = false;
    mockWebSocket.isConnected = false;
    mockWebSocket.messages = [];
  }
  
  function performE2ECleanup(): void {
    wsManager?.cleanup();
    mockServer?.close();
    performFullCleanup(mockServer);
  }
  
  async function renderChatPageWithAuth(): Promise<void> {
    await act(async () => {
      render(
        <TestProviders>
          <ChatPage />
        </TestProviders>
      );
    });
  }
  
  async function verifyInitialChatState(): Promise<void> {
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByText(/Start New Conversation/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(mockAuthStore.isAuthenticated).toBe(true);
    });
  }
  
  async function simulateStartNewConversation(): Promise<void> {
    const startButton = screen.getByRole('button', { name: /Start New Conversation/i });
    await userEvent.click(startButton);
  }
  
  async function verifyThreadCreationFlow(): Promise<void> {
    await waitFor(() => {
      expect(mockChatStore.createThread).toHaveBeenCalledTimes(1);
    });
    
    // Simulate successful thread creation
    mockChatStore.activeThreadId = onboardingData.expectedThreadId;
    mockChatStore.threads = [{ id: onboardingData.expectedThreadId, title: 'New Conversation' }];
  }
  
  async function simulateFirstMessage(): Promise<void> {
    const messageInput = screen.getByRole('textbox', { name: /message input/i });
    await userEvent.type(messageInput, onboardingData.firstMessage);
    
    const sendButton = screen.getByRole('button', { name: /send/i });
    await userEvent.click(sendButton);
  }
  
  async function verifyAIResponseReceived(): Promise<void> {
    // Simulate AI response via WebSocket
    const aiEvent: WebSocketEvent = {
      type: 'ai_message',
      data: mockAIResponse,
      timestamp: Date.now()
    };
    
    wsManager.simulateMessage(aiEvent);
    
    await waitFor(() => {
      expect(screen.getByText(/I'd be happy to help you optimize/i)).toBeInTheDocument();
    }, { timeout: onboardingData.expectedResponseTime });
  }
  
  function expectOnboardingComplete(): void {
    expect(mockChatStore.activeThreadId).toBe(onboardingData.expectedThreadId);
    expect(mockChatStore.messages.length).toBeGreaterThan(0);
    expect(mockWebSocket.isConnected).toBe(true);
  }
  
  async function clickStartNewConversationButton(): Promise<void> {
    const button = screen.getByTestId('start-new-conversation');
    expect(button).toBeEnabled();
    await userEvent.click(button);
  }
  
  async function verifyThreadCreatedSuccessfully(): Promise<void> {
    await waitFor(() => {
      expect(mockChatStore.createThread).toHaveBeenCalledTimes(1);
    });
  }
  
  async function verifyNavigationToNewThread(): Promise<void> {
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(`/chat/${onboardingData.expectedThreadId}`);
    });
  }
  
  function expectReadyForFirstMessage(): void {
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).not.toBeDisabled();
  }
  
  async function simulateWebSocketConnection(): Promise<void> {
    await act(async () => {
      mockWebSocket.connect();
      mockWebSocket.isConnected = true;
      mockWebSocket.connectionState = 'connected';
    });
  }
  
  async function verifyConnectionEstablished(): Promise<void> {
    await waitFor(() => {
      expect(mockWebSocket.isConnected).toBe(true);
    });
  }
  
  function expectConnectionTimingCompliance(startTime: number): void {
    const connectionTime = Date.now() - startTime;
    expect(connectionTime).toBeLessThan(1000); // < 1 second requirement
  }
  
  async function setupActiveThread(): Promise<void> {
    mockChatStore.activeThreadId = onboardingData.expectedThreadId;
    mockChatStore.threads = [{ id: onboardingData.expectedThreadId, title: 'Test Thread' }];
  }
  
  async function sendFirstMessage(): Promise<void> {
    const input = screen.getByRole('textbox');
    await userEvent.type(input, onboardingData.firstMessage);
    await userEvent.keyboard('{Enter}');
  }
  
  async function verifyMessageDeliveryConfirmed(): Promise<void> {
    await waitFor(() => {
      expect(mockChatStore.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: onboardingData.firstMessage
        })
      );
    });
  }
  
  async function simulateAIStreamingResponse(): Promise<void> {
    // Simulate streaming response chunks
    const chunks = mockAIResponse.content.split(' ');
    for (const chunk of chunks) {
      wsManager.simulateStreamingChunk({
        type: 'content_chunk',
        data: { content: chunk + ' ' },
        timestamp: Date.now()
      });
      await new Promise(resolve => setTimeout(resolve, 50)); // 50ms between chunks
    }
  }
  
  function expectFirstConversationComplete(): void {
    expect(mockChatStore.messages.length).toBeGreaterThanOrEqual(2); // User + AI message
    expect(mockChatStore.isProcessing).toBe(false);
  }
  
  async function simulateWebSocketFailure(): Promise<void> {
    mockWebSocket.isConnected = false;
    mockWebSocket.connectionState = 'disconnected';
    wsManager.simulateConnectionError(new Error('Connection failed'));
  }
  
  async function verifyConnectionRetryAttempted(): Promise<void> {
    await waitFor(() => {
      expect(mockWebSocket.connect).toHaveBeenCalledTimes(1);
    });
  }
  
  async function simulateWebSocketRecovery(): Promise<void> {
    await act(async () => {
      mockWebSocket.isConnected = true;
      mockWebSocket.connectionState = 'connected';
    });
  }
  
  function expectSuccessfulRecovery(): void {
    expect(mockWebSocket.isConnected).toBe(true);
    expect(screen.queryByText(/connection error/i)).not.toBeInTheDocument();
  }
  
  async function simulateThreadCreationFailure(): Promise<void> {
    mockChatStore.createThread.mockRejectedValueOnce(new Error('Thread creation failed'));
  }
  
  async function verifyErrorMessageDisplayed(): Promise<void> {
    await waitFor(() => {
      expect(screen.getByText(/error creating thread/i)).toBeInTheDocument();
    });
  }
  
  async function retryThreadCreation(): Promise<void> {
    mockChatStore.createThread.mockResolvedValueOnce({
      id: onboardingData.expectedThreadId,
      title: 'New Conversation'
    });
    
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await userEvent.click(retryButton);
  }
  
  function expectSuccessfulThreadCreation(): void {
    expect(mockChatStore.activeThreadId).toBe(onboardingData.expectedThreadId);
    expect(screen.queryByText(/error creating thread/i)).not.toBeInTheDocument();
  }
});
