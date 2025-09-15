/**
 * Unit Test: useMessageSending Hook Thread ID Validation
 * 
 * Tests for Issue #1141: Frontend thread ID confusion - thread_id: null issue
 * 
 * This test should FAIL initially to reproduce the issue where thread_id 
 * is sent as null instead of the expected thread ID from the URL parameter.
 * 
 * Expected Failure Mode: thread_id should be 'thread_2_5e5c7cac' but will be null
 */

import { renderHook, act } from '@testing-library/react';
import { useMessageSending } from '@/components/chat/hooks/useMessageSending';
import { useThreadStore } from '@/store/threadStore';
import { WebSocketMessageType } from '@/types/shared/enums';

// Mock dependencies
jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(),
}));
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(),
}));
jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(),
}));
jest.mock('@/services/threadService');
jest.mock('@/services/threadRenameService');
jest.mock('@/services/optimistic-updates');
jest.mock('@/lib/logger');
jest.mock('@/hooks/useGTMEvent', () => ({
  useGTMEvent: jest.fn(),
}));
jest.mock('@/services/analyticsService', () => ({
  useAnalytics: jest.fn(),
}));
jest.mock('@/lib/unified-api-config');
jest.mock('@/services/agentServiceV2');

describe('useMessageSending - Thread ID Propagation (Issue #1141)', () => {
  // Mock implementations
  const mockSendMessage = jest.fn();
  const { useWebSocket } = require('@/hooks/useWebSocket');
  const { useUnifiedChatStore } = require('@/store/unified-chat');
  const { useThreadStore } = require('@/store/threadStore');
  const { useGTMEvent } = require('@/hooks/useGTMEvent');
  const { useAnalytics } = require('@/services/analyticsService');

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock WebSocket hook
    useWebSocket.mockReturnValue({
      sendMessage: mockSendMessage,
    });
    
    // Mock unified chat store
    useUnifiedChatStore.mockReturnValue({
      addMessage: jest.fn(),
      setActiveThread: jest.fn(),
      setProcessing: jest.fn(),
      addOptimisticMessage: jest.fn(),
      updateOptimisticMessage: jest.fn(),
      messages: [], // Empty messages array simulates first message
    });
    
    // Mock thread store with specific thread ID
    useThreadStore.mockReturnValue({
      setCurrentThread: jest.fn(),
      addThread: jest.fn(),
    });
    
    // Mock GTM events
    useGTMEvent.mockReturnValue({
      trackChatStarted: jest.fn(),
      trackMessageSent: jest.fn(),
      trackThreadCreated: jest.fn(),
      trackError: jest.fn(),
      trackAgentActivated: jest.fn(),
    });
    
    // Mock analytics
    useAnalytics.mockReturnValue({
      trackFeatureUsage: jest.fn(),
      trackInteraction: jest.fn(),
      trackError: jest.fn(),
    });
    
    // Mock unified API config
    require('@/lib/unified-api-config').shouldUseV2AgentApi.mockReturnValue(false);
    require('@/lib/unified-api-config').getUnifiedApiConfig.mockReturnValue({});
  });

  test('SHOULD FAIL: thread_id should be propagated correctly but will be null', async () => {
    // Arrange: Set up scenario with specific thread ID from URL
    const expectedThreadId = 'thread_2_5e5c7cac';
    
    // This simulates the scenario where user navigates to /chat/thread_2_5e5c7cac
    // The ThreadStore should have this thread ID, but it's not being properly propagated
    const messageSendingParams = {
      message: 'Test message for thread ID propagation',
      isAuthenticated: true,
      activeThreadId: expectedThreadId, // This should be passed to WebSocket
      currentThreadId: null,
    };
    
    // Act: Render the hook and call handleSend
    const { result } = renderHook(() => useMessageSending());
    
    let capturedWebSocketMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedWebSocketMessage = message;
    });
    
    await act(async () => {
      await result.current.handleSend(messageSendingParams);
    });
    
    // Assert: Check that thread_id is properly set in WebSocket message
    expect(mockSendMessage).toHaveBeenCalled();
    expect(capturedWebSocketMessage).toBeDefined();
    expect(capturedWebSocketMessage.type).toBe(WebSocketMessageType.START_AGENT);
    
    // CRITICAL ASSERTION - This should FAIL initially
    // The bug is that thread_id will be null instead of the expected thread ID
    expect(capturedWebSocketMessage.payload.thread_id).toBe(expectedThreadId);
    
    // Additional assertion for debugging
    console.log('Captured WebSocket message:', JSON.stringify(capturedWebSocketMessage, null, 2));
    
    // This test should FAIL with: 
    // Expected thread_id: 'thread_2_5e5c7cac', got: null
    expect(capturedWebSocketMessage.payload.thread_id).not.toBeNull();
    expect(capturedWebSocketMessage.payload.thread_id).not.toBeUndefined();
  });

  test('SHOULD FAIL: thread_id null issue reproduction with different thread ID', async () => {
    // Test with different thread ID format to ensure it's not specific to one format
    const expectedThreadId = 'thread_1_abc123def';
    
    const messageSendingParams = {
      message: 'Another test message',
      isAuthenticated: true,
      activeThreadId: expectedThreadId,
      currentThreadId: null,
    };
    
    const { result } = renderHook(() => useMessageSending());
    
    let capturedMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedMessage = message;
    });
    
    await act(async () => {
      await result.current.handleSend(messageSendingParams);
    });
    
    // This should also FAIL - thread_id will be null
    expect(capturedMessage.payload.thread_id).toBe(expectedThreadId);
    
    // Log for debugging
    if (capturedMessage.payload.thread_id === null) {
      console.log('BUG REPRODUCED: thread_id is null when it should be:', expectedThreadId);
    }
  });

  test('SHOULD FAIL: currentThreadId fallback also produces null thread_id', async () => {
    // Test scenario where activeThreadId is null but currentThreadId has value
    const expectedThreadId = 'thread_3_xyz789';
    
    const messageSendingParams = {
      message: 'Test with currentThreadId fallback',
      isAuthenticated: true,
      activeThreadId: null, // null active thread
      currentThreadId: expectedThreadId, // should fall back to this
    };
    
    const { result } = renderHook(() => useMessageSending());
    
    let capturedMessage: any = null;
    mockSendMessage.mockImplementation((message) => {
      capturedMessage = message;
    });
    
    await act(async () => {
      await result.current.handleSend(messageSendingParams);
    });
    
    // This should FAIL - even with currentThreadId, thread_id will be null  
    expect(capturedMessage.payload.thread_id).toBe(expectedThreadId);
    
    console.log('Fallback test - captured thread_id:', capturedMessage.payload.thread_id);
  });
});