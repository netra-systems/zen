/**
 * Unit tests for agent_response WebSocket handler
 * REGRESSION TEST: Ensures agent_response messages are properly handled
 * Related to: SPEC/learnings/websocket_agent_response_missing_handler.xml
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import {
  extractAgentResponseData,
  createAgentResponseMessage,
  handleAgentResponse
} from '@/store/websocket-agent-handlers';
import { parseTimestamp } from '@/store/websocket-event-handlers-core';
import { MessageFormatterService } from '@/services/messageFormatter';
import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';
import type { UnifiedChatState } from '@/types/store-types';

// Mock dependencies
jest.mock('@/store/websocket-event-handlers-core', () => ({
  parseTimestamp: jest.fn((ts) => typeof ts === 'number' ? ts * 1000 : Date.now())
}));

jest.mock('@/services/messageFormatter', () => ({
  MessageFormatterService: {
    enrich: jest.fn((msg) => ({ ...msg, formatted: true }))
  }
}));

jest.mock('@/lib/utils', () => ({
  generateUniqueId: jest.fn((prefix) => `${prefix}-test-123`)
}));

describe('WebSocket Agent Response Handler', () => {
  let mockGet: jest.Mock;
  let mockSet: jest.Mock;
  let mockAddMessage: jest.Mock;
  let mockState: Partial<UnifiedChatState>;

  beforeEach(() => {
    jest.clearAllMocks();
    mockAddMessage = jest.fn();
    mockGet = jest.fn(() => ({ addMessage: mockAddMessage }));
    mockSet = jest.fn();
    mockState = {
      messages: [],
      isProcessing: false
    };
  });

  describe('extractAgentResponseData', () => {
    it('should extract content from direct fields', () => {
      const payload = {
        content: 'Test response',
        thread_id: 'thread-123',
        user_id: 'user-456',
        timestamp: 1234567890
      };

      const result = extractAgentResponseData(payload);

      expect(result.content).toBe('Test response');
      expect(result.threadId).toBe('thread-123');
      expect(result.userId).toBe('user-456');
      expect(result.timestamp).toBeDefined();
    });

    it('should extract content from message field as fallback', () => {
      const payload = {
        message: 'Fallback response',
        thread_id: 'thread-789'
      };

      const result = extractAgentResponseData(payload);

      expect(result.content).toBe('Fallback response');
      expect(result.threadId).toBe('thread-789');
    });

    it('should extract content from nested data.content', () => {
      const payload = {
        data: {
          content: 'Nested response',
          message: 'Should not use this'
        },
        thread_id: 'thread-nested'
      };

      const result = extractAgentResponseData(payload);

      expect(result.content).toBe('Nested response');
    });

    it('should handle missing content gracefully', () => {
      const payload = {
        thread_id: 'thread-empty'
      };

      const result = extractAgentResponseData(payload);

      expect(result.content).toBe('');
      expect(result.threadId).toBe('thread-empty');
    });

    it('should handle camelCase threadId', () => {
      const payload = {
        content: 'Test',
        threadId: 'camel-thread',
        userId: 'camel-user'
      };

      const result = extractAgentResponseData(payload);

      expect(result.threadId).toBe('camel-thread');
      expect(result.userId).toBe('camel-user');
    });
  });

  describe('createAgentResponseMessage', () => {
    it('should create and add a message with content', () => {
      const responseData = {
        content: 'Agent response message',
        threadId: 'thread-123',
        userId: 'user-456',
        timestamp: Date.now(),
        agentData: { status: 'success' }
      };

      createAgentResponseMessage(responseData, mockGet as any);

      expect(mockAddMessage).toHaveBeenCalledTimes(1);
      const message = mockAddMessage.mock.calls[0][0];
      
      expect(message.role).toBe('assistant');
      expect(message.content).toBe('Agent response message');
      expect(message.metadata.source).toBe('agent_response');
      expect(message.metadata.threadId).toBe('thread-123');
      expect(message.metadata.userId).toBe('user-456');
      expect(message.metadata.status).toBe('success');
      expect(message.formatted).toBe(true); // From MessageFormatterService mock
    });

    it('should not add message when content is empty', () => {
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      const responseData = {
        content: '',
        threadId: 'thread-123',
        timestamp: Date.now(),
        agentData: {}
      };

      createAgentResponseMessage(responseData, mockGet as any);

      expect(mockAddMessage).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Agent response missing content:',
        responseData
      );

      consoleWarnSpy.mockRestore();
    });

    it('should generate unique message ID', () => {
      const responseData = {
        content: 'Test message',
        threadId: 'thread-123',
        timestamp: Date.now(),
        agentData: {}
      };

      createAgentResponseMessage(responseData, mockGet as any);

      const message = mockAddMessage.mock.calls[0][0];
      expect(message.id).toBe('agent-resp-test-123');
    });
  });

  describe('handleAgentResponse', () => {
    it('should process agent_response event', () => {
      const event: UnifiedWebSocketEvent = {
        type: 'agent_response',
        payload: {
          content: 'Full response from agent',
          thread_id: 'thread-456',
          user_id: 'user-789',
          timestamp: 1234567890,
          data: {
            agents_involved: ['triage'],
            status: 'success'
          }
        }
      };

      handleAgentResponse(event, mockState as any, mockSet, mockGet as any);

      expect(mockAddMessage).toHaveBeenCalledTimes(1);
      const message = mockAddMessage.mock.calls[0][0];
      
      expect(message.content).toBe('Full response from agent');
      expect(message.role).toBe('assistant');
      expect(message.metadata.agents_involved).toEqual(['triage']);
    });

    it('should handle real-world backend message format', () => {
      // This is the actual format from the backend
      const event: UnifiedWebSocketEvent = {
        type: 'agent_response',
        payload: {
          type: 'agent_response',
          content: "Agent response for: Hello",
          message: "Agent response for: Hello",
          user_id: 'dev-temp-6f6e3952',
          thread_id: 'thread-real',
          timestamp: 1756681580.140139,
          data: {
            status: 'success',
            content: "Agent response for: Hello",
            message: "Agent response for: Hello",
            agents_involved: ['triage'],
            orchestration_time: 0.8,
            response_time: 0.8,
            real_llm_used: false,
            turn_id: 'unknown'
          }
        }
      };

      handleAgentResponse(event, mockState as any, mockSet, mockGet as any);

      expect(mockAddMessage).toHaveBeenCalledTimes(1);
      const message = mockAddMessage.mock.calls[0][0];
      
      expect(message.content).toBe("Agent response for: Hello");
      expect(message.metadata.orchestration_time).toBe(0.8);
      expect(message.metadata.real_llm_used).toBe(false);
    });

    it('should not crash with malformed payload', () => {
      const event: UnifiedWebSocketEvent = {
        type: 'agent_response',
        payload: null as any
      };

      expect(() => {
        handleAgentResponse(event, mockState as any, mockSet, mockGet as any);
      }).not.toThrow();
    });
  });

  describe('Integration with Event Registry', () => {
    it('should be registered in event handlers', async () => {
      // Dynamic import to test registration
      const { getEventHandlers } = await import('@/store/websocket-event-handlers-main');
      const handlers = getEventHandlers();
      
      expect(handlers['agent_response']).toBeDefined();
      expect(typeof handlers['agent_response']).toBe('function');
    });
  });
});

describe('Regression Prevention', () => {
  it('should have handler for agent_response to prevent UI display failure', () => {
    // This test ensures the critical bug doesn't resurface
    // where agent_response messages were silently dropped
    
    const criticalMessageTypes = [
      'agent_started',
      'agent_response',  // CRITICAL: This was missing before
      'agent_completed',
      'agent_thinking',
      'tool_executing',
      'tool_completed',
      'error'
    ];

    const { getEventHandlers } = require('@/store/websocket-event-handlers-main');
    const handlers = getEventHandlers();

    criticalMessageTypes.forEach(type => {
      expect(handlers[type]).toBeDefined();
      expect(handlers[type]).not.toBeNull();
      expect(typeof handlers[type]).toBe('function');
    });
  });
});