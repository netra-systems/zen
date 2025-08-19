/**
 * AI Message Performance Tests
 * 
 * Tests rendering performance, rapid updates, and complex message handling.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test definitions
 * @compliance no_test_stubs.xml - Real implementations only
 */

import React from 'react';
import { render } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';
import { Message } from '@/types/registry';
import { setupChatMocks, resetChatMocks, renderWithChatSetup } from './shared-test-setup';

// ============================================================================
// TEST SETUP
// ============================================================================

beforeAll(() => {
  setupChatMocks();
});

beforeEach(() => {
  resetChatMocks();
});

// ============================================================================
// TEST DATA FACTORIES
// ============================================================================

const createAIMessage = (overrides: Partial<Message> = {}): Message => ({
  id: 'ai-msg-1',
  role: 'assistant',
  type: 'agent',
  content: 'AI response message',
  sub_agent_name: 'OptimizationAgent',
  created_at: '2023-01-01T12:00:00Z',
  displayed_to_user: true,
  thread_id: 'thread-1',
  ...overrides
});

// ============================================================================
// PERFORMANCE TESTS
// ============================================================================

describe('AIMessage - Performance', () => {
  it('renders complex AI messages within performance budget', () => {
    const complexMessage = createAIMessage({
      content: 'A'.repeat(5000), // 5KB content
      metadata: {
        mcpExecutions: Array(10).fill({
          tool_name: 'test_tool',
          status: 'completed',
          args: { test: 'value' }
        })
      }
    });
    
    const startTime = performance.now();
    renderWithChatSetup(<MessageItem message={complexMessage} />);
    const endTime = performance.now();
    
    expect(endTime - startTime).toBeLessThan(500); // < 500ms render time (relaxed for CI)
  });

  it('handles rapid message updates efficiently', async () => {
    const message = createAIMessage();
    const { rerender } = renderWithChatSetup(<MessageItem message={message} />);
    
    const startTime = performance.now();
    
    // Simulate rapid updates
    for (let i = 0; i < 50; i++) {
      const updatedMessage = {
        ...message,
        content: `${message.content} update ${i}`
      };
      rerender(<MessageItem message={updatedMessage} />);
    }
    
    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(500); // < 500ms for 50 updates
  });
});