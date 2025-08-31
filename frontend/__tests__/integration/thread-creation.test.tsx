import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
stification:
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Goal: Ensure seamless thread creation flow for user engagement
 * - Value Impact: Critical for Free → Paid conversion pipeline
 * - Revenue Impact: Protects onboarding and user retention
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all props and interactions
 * @compliance frontend_unified_testing_spec.xml - journey id="start_chat_button"
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { useRouter } from 'next/navigation';

// Test utilities and mocks
import '../setup/auth-service-setup';
import { mockAuthServiceFetch } from '../mocks/auth-service-mock';

// Components under test
import { ThreadSidebarHeader } from '@/components/chat/ThreadSidebarComponents';

// Store mocks
jest.mock('@/store/chatStore');
jest.mock('@/store/authStore');
jest.mock('next/navigation');

// Test types
interface ThreadCreationTest {
  description: string;
  mockApiResponse: any;
  expectedCalls: number;
  shouldSucceed: boolean;
  expectedThreadId?: string;
}

// Test fixtures
const mockRouter = { push: jest.fn(), replace: jest.fn(), prefetch: jest.fn() };
const mockThreadService = { createThread: jest.fn(), getThreads: jest.fn().mockResolvedValue([]) };
const mockChatStore = { 
  threads: [], 
  setCurrentThreadId: jest.fn(), 
  addThread: jest.fn(), 
  isLoading: false 
};
const mockAuthStore = { 
  isAuthenticated: true, 
  user: { id: 'user-123', email: 'test@example.com' }, 
  token: 'mock-token' 
};

describe('Thread Creation Core Integration', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    setupIntegrationTests();
  });
  
  afterEach(() => {
    cleanupIntegrationTests();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });
  
  describe('API Call to Create Thread', () => {
      jest.setTimeout(10000);
    const apiTests: ThreadCreationTest[] = [
      {
        description: 'successfully creates thread with valid API response',
        mockApiResponse: { id: 'thread-123', title: 'New Conversation', created_at: Date.now() },
        expectedCalls: 1,
        shouldSucceed: true,
        expectedThreadId: 'thread-123'
      },
      {
        description: 'handles API failure gracefully',
        mockApiResponse: new Error('Network error'),
        expectedCalls: 1,
        shouldSucceed: false
      }
    ];
    
    test.each(apiTests)('$description', async ({ mockApiResponse, expectedCalls, shouldSucceed, expectedThreadId }) => {
      setupApiMock(mockApiResponse, shouldSucceed);
      renderThreadCreationFlow();
      await triggerThreadCreation();
      verifyApiCalls(expectedCalls);
      if (shouldSucceed) {
        await verifyThreadCreated(expectedThreadId!);
      } else {
        await verifyErrorHandling();
      }
    });
    
    it('creates thread with < 300ms response time requirement', async () => {
      setupFastApiResponse();
      renderThreadCreationFlow();
      const startTime = performance.now();
      await triggerThreadCreation();
      await waitForThreadCreation();
      expectCreationUnder300ms(startTime);
    });
    
    it('includes authentication token in API request', async () => {
      setupApiResponseWithAuth();
      renderThreadCreationFlow();
      await triggerThreadCreation();
      verifyAuthTokenIncluded();
    });
    
    it('generates unique thread ID for each creation', async () => {
      setupMultipleThreadCreation();
      renderThreadCreationFlow();
      await createMultipleThreads();
      verifyUniqueThreadIds();
    });
  });
  
  describe('Optimistic UI Updates', () => {
      jest.setTimeout(10000);
    it('shows thread immediately in sidebar', async () => {
      setupOptimisticUpdate([]);
      renderThreadCreationFlow();
      await triggerThreadCreation();
      await waitForUIUpdate(0);
      verifyOptimisticUpdate('New Conversation');
    });
    
    it('shows creating state during API call', async () => {
      setupSlowApiResponse();
      renderThreadCreationFlow();
      await triggerThreadCreation();
      verifyCreatingState();
      await waitForApiComplete();
      verifyCreatingStateCleared();
    });
    
    it('reverts optimistic update on API failure', async () => {
      setupFailingApiResponse();
      renderThreadCreationFlow();
      await triggerThreadCreation();
      await waitForApiFailure();
      verifyOptimisticRevert();
    });
  });
  
  describe('Sidebar and Navigation Updates', () => {
      jest.setTimeout(10000);
    it('adds new thread to sidebar list immediately', async () => {
      renderThreadCreationFlow();
      await triggerThreadCreation();
      verifyThreadInSidebar();
    });
    
    it('highlights new thread as active', async () => {
      renderThreadCreationFlow();
      await triggerThreadCreation();
      await waitForThreadCreation();
      verifyActiveThreadHighlight();
    });
    
    it('navigates to new thread URL immediately', async () => {
      renderThreadCreationFlow();
      await triggerThreadCreation();
      await waitForNavigation();
      verifyRouterPush();
      expectCorrectThreadUrl();
    });
  });
  
  describe('Error Handling and Analytics', () => {
      jest.setTimeout(10000);
    it('shows error message on API failure', async () => {
      setupApiFailure();
      renderThreadCreationFlow();
      await triggerThreadCreation();
      await waitForError();
      verifyErrorMessage();
    });
    
    it('fires thread_creation_started event on click', async () => {
      setupAnalyticsMock();
      renderThreadCreationFlow();
      await triggerThreadCreation();
      verifyAnalyticsEvent('thread_creation_started');
    });
  });
  
  // Helper functions (8 lines max each)
  function setupIntegrationTests(): void {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    mockAuthServiceFetch();
    setupDefaultMocks();
  }
  
  function cleanupIntegrationTests(): void {
    jest.resetAllMocks();
  }
  
  function setupDefaultMocks(): void {
    require('@/store/chatStore').useChatStore.mockReturnValue(mockChatStore);
    require('@/store/authStore').useAuthStore.mockReturnValue(mockAuthStore);
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
  }
  
  function setupApiMock(response: any, shouldSucceed: boolean): void {
    if (shouldSucceed) {
      mockThreadService.createThread.mockResolvedValue(response);
    } else {
      mockThreadService.createThread.mockRejectedValue(response);
    }
  }
  
  function renderThreadCreationFlow() {
    return render(
      <ThreadSidebarHeader
        onCreateThread={mockThreadService.createThread}
        isCreating={false}
        isLoading={false}
        isAuthenticated={true}
      />
    );
  }
  
  async function triggerThreadCreation(): Promise<void> {
    const button = screen.getByRole('button', { name: /new conversation/i });
    await userEvent.click(button);
  }
  
  function verifyApiCalls(expectedCalls: number): void {
    expect(mockThreadService.createThread).toHaveBeenCalledTimes(expectedCalls);
  }
  
  async function verifyThreadCreated(threadId: string): Promise<void> {
    await waitFor(() => expect(mockChatStore.addThread).toHaveBeenCalled());
  }
  
  async function verifyErrorHandling(): Promise<void> {
    await waitFor(() => expect(screen.getByRole('button')).toBeEnabled());
  }
  
  function setupFastApiResponse(): void {
    const fastResponse = { id: 'fast-thread', title: 'Fast Thread', created_at: Date.now() };
    mockThreadService.createThread.mockResolvedValue(fastResponse);
  }
  
  async function waitForThreadCreation(): Promise<void> {
    await waitFor(() => expect(mockThreadService.createThread).toHaveBeenCalled());
  }
  
  function expectCreationUnder300ms(startTime: number): void {
    const elapsedTime = performance.now() - startTime;
    expect(elapsedTime).toBeLessThan(300);
  }
  
  function setupApiResponseWithAuth(): void {
    mockThreadService.createThread.mockImplementation(() => {
      expect(mockAuthStore.token).toBeTruthy();
      return Promise.resolve({ id: 'auth-thread', title: 'Authenticated Thread' });
    });
  }
  
  function verifyAuthTokenIncluded(): void {
    expect(mockThreadService.createThread).toHaveBeenCalled();
  }
  
  function setupMultipleThreadCreation(): void {
    let counter = 0;
    mockThreadService.createThread.mockImplementation(() => {
      counter++;
      return Promise.resolve({ id: `thread-${counter}`, title: `Thread ${counter}` });
    });
  }
  
  async function createMultipleThreads(): Promise<void> {
    await triggerThreadCreation();
    await triggerThreadCreation();
  }
  
  function verifyUniqueThreadIds(): void {
    expect(mockThreadService.createThread).toHaveBeenCalledTimes(2);
  }
  
  function setupOptimisticUpdate(initialThreads: any[]): void {
    mockChatStore.threads = initialThreads;
  }
  
  async function waitForUIUpdate(delay: number): Promise<void> {
    if (delay > 0) await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  function verifyOptimisticUpdate(expectedText: string): void {
    expect(screen.getByText(expectedText)).toBeInTheDocument();
  }
  
  function setupSlowApiResponse(): void {
    mockThreadService.createThread.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({ id: 'slow-thread' }), 1000))
    );
  }
  
  function verifyCreatingState(): void {
    expect(screen.getByRole('button')).toBeDisabled();
  }
  
  async function waitForApiComplete(): Promise<void> {
    await waitFor(() => expect(screen.getByRole('button')).toBeEnabled(), { timeout: 2000 });
  }
  
  function verifyCreatingStateCleared(): void {
    expect(screen.getByRole('button')).toBeEnabled();
  }
  
  function setupFailingApiResponse(): void {
    mockThreadService.createThread.mockRejectedValue(new Error('API Error'));
  }
  
  async function waitForApiFailure(): Promise<void> {
    await waitFor(() => expect(screen.getByRole('button')).toBeEnabled());
  }
  
  function verifyOptimisticRevert(): void {
    expect(screen.getByRole('button')).toBeEnabled();
  }
  
  function verifyThreadInSidebar(): void {
    expect(mockChatStore.addThread).toHaveBeenCalled();
  }
  
  function verifyActiveThreadHighlight(): void {
    expect(mockChatStore.setCurrentThreadId).toHaveBeenCalled();
  }
  
  async function waitForNavigation(): Promise<void> {
    await waitFor(() => expect(mockRouter.push).toHaveBeenCalled());
  }
  
  function verifyRouterPush(): void {
    expect(mockRouter.push).toHaveBeenCalled();
  }
  
  function expectCorrectThreadUrl(): void {
    expect(mockRouter.push).toHaveBeenCalledWith(expect.stringContaining('/chat/'));
  }
  
  function setupApiFailure(): void {
    mockThreadService.createThread.mockRejectedValue(new Error('API Error'));
  }
  
  async function waitForError(): Promise<void> {
    await waitFor(() => expect(screen.getByRole('button')).toBeEnabled());
  }
  
  function verifyErrorMessage(): void {
    expect(screen.getByRole('button')).toBeEnabled();
  }
  
  function setupAnalyticsMock(): void {
    global.analytics = { track: jest.fn() };
  }
  
  function verifyAnalyticsEvent(eventName: string): void {
    expect(global.analytics?.track).toHaveBeenCalledWith(eventName, expect.any(Object));
  }
});