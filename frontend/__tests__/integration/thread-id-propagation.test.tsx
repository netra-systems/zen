/**
 * Integration Test: Thread ID Propagation Flow
 * 
 * Tests for Issue #1141: Frontend thread ID confusion - thread_id: null issue
 * 
 * This test should FAIL initially to reproduce the integration issue where
 * the thread ID from URL parameter → ThreadStore → MessageSending flow breaks.
 * 
 * Expected Failure Mode: Integration breaks thread ID propagation between components
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/router';
import { useThreadStore } from '@/store/threadStore';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { MessageInput } from '@/components/chat/MessageInput';
import { WebSocketMessageType } from '@/types/shared/enums';
import React from 'react';

// Mock Next.js router
jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

// Mock dependencies
jest.mock('@/store/threadStore');
jest.mock('@/store/unified-chat');
jest.mock('@/hooks/useWebSocket');
jest.mock('@/hooks/useGTMEvent');
jest.mock('@/services/analyticsService');
jest.mock('@/lib/unified-api-config');
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/services/optimistic-updates');
jest.mock('@/lib/logger');

// Test Component wrapper that simulates the real chat page
const TestChatPageWrapper: React.FC<{ threadId: string; children: React.ReactNode }> = ({ 
  threadId, 
  children 
}) => {
  // This simulates how the real chat page would extract thread ID from URL
  const mockUseThreadStore = useThreadStore as jest.MockedFunction<typeof useThreadStore>;
  
  React.useEffect(() => {
    // Simulate thread store getting updated with URL thread ID
    const threadStore = mockUseThreadStore();
    if (threadStore.setCurrentThread) {
      threadStore.setCurrentThread(threadId);
    }
  }, [threadId]);
  
  return <>{children}</>;
};

describe('Integration Test: Thread ID Propagation (Issue #1141)', () => {
  // Mock implementations
  const mockSendMessage = jest.fn();
  const mockPush = jest.fn();
  const mockQuery = { thread_id: 'thread_2_5e5c7cac' };
  
  const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;
  const mockUseThreadStore = useThreadStore as jest.MockedFunction<typeof useThreadStore>;
  const mockUseUnifiedChatStore = useUnifiedChatStore as jest.MockedFunction<typeof useUnifiedChatStore>;
  const mockUseWebSocket = useWebSocket as jest.MockedFunction<typeof useWebSocket>;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock Next.js router with thread ID in URL
    mockUseRouter.mockReturnValue({
      push: mockPush,
      query: mockQuery,
      pathname: '/chat/[thread_id]',
      asPath: '/chat/thread_2_5e5c7cac',
      route: '/chat/[thread_id]',
      events: {
        on: jest.fn(),
        off: jest.fn(),
        emit: jest.fn(),
      },
      beforePopState: jest.fn(),
      prefetch: jest.fn(),
      reload: jest.fn(),
      replace: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      isReady: true,
      isFallback: false,
      isLocaleDomain: true,
      isPreview: false,
      basePath: '',
      locale: undefined,
      locales: undefined,
      defaultLocale: undefined,
      domainLocales: undefined,
    });
    
    // Mock thread store - simulates real behavior
    mockUseThreadStore.mockReturnValue({
      threads: [
        {
          id: 'thread_2_5e5c7cac',
          name: 'Test Thread',
          title: 'Test Thread',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          metadata: {},
        }
      ],
      currentThreadId: 'thread_2_5e5c7cac', // This should be set from URL
      currentThread: {
        id: 'thread_2_5e5c7cac',
        name: 'Test Thread',
        title: 'Test Thread',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metadata: {},
      },
      loading: false,
      error: null,
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
      updateThread: jest.fn(),
      deleteThread: jest.fn(),
      setThreads: jest.fn(),
      clearCurrentThread: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn(),
      reset: jest.fn(),
    });
    
    // Mock unified chat store
    mockUseUnifiedChatStore.mockReturnValue({
      messages: [], // Empty messages simulates first message
      activeThreadId: 'thread_2_5e5c7cac', // Should come from thread store
      isProcessing: false,
      error: null,
      addMessage: jest.fn(),
      setActiveThread: jest.fn(),
      setProcessing: jest.fn(),
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
      removeOptimisticMessage: jest.fn(),
      clearMessages: jest.fn(),
      setError: jest.fn(),
      reset: jest.fn(),
    });
    
    // Mock WebSocket
    mockUseWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
      isConnected: true,
      isConnecting: false,
      lastMessage: null,
      error: null,
      reconnect: jest.fn(),
      disconnect: jest.fn(),
    });
    
    // Mock other dependencies
    require('@/hooks/useGTMEvent').useGTMEvent.mockReturnValue({
      trackChatStarted: jest.fn(),
      trackMessageSent: jest.fn(),
      trackThreadCreated: jest.fn(),
      trackError: jest.fn(),
      trackAgentActivated: jest.fn(),
    });
    
    require('@/services/analyticsService').useAnalytics.mockReturnValue({
      trackFeatureUsage: jest.fn(),
      trackInteraction: jest.fn(),
      trackError: jest.fn(),
    });
    
    require('@/lib/unified-api-config').shouldUseV2AgentApi.mockReturnValue(false);
  });

  test('SHOULD FAIL: Thread ID from URL should propagate to WebSocket message', async () => {
    // Arrange: Render MessageInput within context that has thread ID from URL
    const expectedThreadId = 'thread_2_5e5c7cac';
    const testMessage = 'Test message for integration flow';
    
    let capturedWebSocketMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedWebSocketMessage = message;
      console.log('Integration test captured WebSocket message:', JSON.stringify(message, null, 2));
    });
    
    // Act: Render component with thread context
    render(
      <TestChatPageWrapper threadId={expectedThreadId}>
        <MessageInput 
          value=""
          onChange={() => {}}
          onSend={() => {}}
          isProcessing={false}
          disabled={false}
        />
      </TestChatPageWrapper>
    );
    
    // Find the input and submit button (based on MessageInput implementation)
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    // Type message and send
    await userEvent.type(textarea, testMessage);
    await userEvent.click(sendButton);
    
    // Wait for async operations
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalled();
    });
    
    // Assert: Check that thread_id is properly propagated through the integration flow
    expect(capturedWebSocketMessage).toBeDefined();
    expect(capturedWebSocketMessage.type).toBe(WebSocketMessageType.START_AGENT);
    
    // CRITICAL ASSERTION - This should FAIL
    // The integration flow breaks thread ID propagation
    expect(capturedWebSocketMessage.payload.thread_id).toBe(expectedThreadId);
    
    // Debugging information
    console.log('Expected thread_id:', expectedThreadId);
    console.log('Actual thread_id:', capturedWebSocketMessage?.payload?.thread_id);
    console.log('Full payload:', capturedWebSocketMessage?.payload);
    
    // This should FAIL with: Integration breaks thread ID propagation
    expect(capturedWebSocketMessage.payload.thread_id).not.toBeNull();
    expect(capturedWebSocketMessage.payload.thread_id).not.toBeUndefined();
  });

  test('SHOULD FAIL: Thread store currentThreadId not being used by MessageSending', async () => {
    // Test that even when ThreadStore has correct currentThreadId, 
    // MessageSending doesn't use it properly
    
    const expectedThreadId = 'thread_2_5e5c7cac';
    const testMessage = 'Another integration test message';
    
    // Ensure thread store has the correct thread ID
    const threadStore = mockUseThreadStore();
    expect(threadStore.currentThreadId).toBe(expectedThreadId);
    
    let capturedMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedMessage = message;
    });
    
    render(
      <TestChatPageWrapper threadId={expectedThreadId}>
        <MessageInput 
          value=""
          onChange={() => {}}
          onSend={() => {}}
          isProcessing={false}
          disabled={false}
        />
      </TestChatPageWrapper>
    );
    
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    await userEvent.type(textarea, testMessage);
    await userEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalled();
    });
    
    // This should FAIL - MessageSending doesn't properly read from ThreadStore
    expect(capturedMessage.payload.thread_id).toBe(expectedThreadId);
    
    if (capturedMessage.payload.thread_id === null) {
      console.log('BUG CONFIRMED: ThreadStore has thread ID but MessageSending sends null');
      console.log('ThreadStore currentThreadId:', threadStore.currentThreadId);
      console.log('WebSocket message thread_id:', capturedMessage.payload.thread_id);
    }
  });

  test('SHOULD FAIL: activeThreadId from chat store also produces null', async () => {
    // Test that even when UnifiedChatStore has activeThreadId, it's still null in WebSocket
    const expectedThreadId = 'thread_2_5e5c7cac';
    
    // Verify that chat store has the active thread ID
    const chatStore = mockUseUnifiedChatStore();
    expect(chatStore.activeThreadId).toBe(expectedThreadId);
    
    let capturedMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedMessage = message;
    });
    
    render(
      <TestChatPageWrapper threadId={expectedThreadId}>
        <MessageInput 
          value=""
          onChange={() => {}}
          onSend={() => {}}
          isProcessing={false}
          disabled={false}
        />
      </TestChatPageWrapper>
    );
    
    const textarea = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });
    
    await userEvent.type(textarea, 'Chat store thread ID test');
    await userEvent.click(sendButton);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalled();
    });
    
    // This should FAIL - even with activeThreadId set, WebSocket gets null
    expect(capturedMessage.payload.thread_id).toBe(expectedThreadId);
    
    console.log('Chat store activeThreadId:', chatStore.activeThreadId);
    console.log('WebSocket thread_id:', capturedMessage?.payload?.thread_id);
  });
});