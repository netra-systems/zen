/**
 * AI Message Display Tests
 * 
 * Tests AI-specific message display styling, alignment, and visual elements.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed test definitions
 * @compliance no_test_stubs.xml - Real implementations only
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
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
// AI MESSAGE STYLING TESTS
// ============================================================================

describe('AIMessage - Display and Styling', () => {
  it('renders AI message with correct styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const messageContainer = screen.getByText('OptimizationAgent').closest('.mb-4');
    expect(messageContainer).toHaveClass('justify-start');
    expect(screen.getByText('OptimizationAgent')).toBeInTheDocument();
  });

  it('displays AI avatar with gradient styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const avatar = screen.getByText('AI');
    expect(avatar).toHaveClass('from-purple-600', 'to-pink-600');
  });

  it('applies AI-specific card styling', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const card = screen.getByText('OptimizationAgent').closest('.rounded-lg');
    expect(card).toHaveClass('border-gray-200');
  });

  it('aligns AI message to the left', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const container = screen.getByText('OptimizationAgent').closest('.mb-4');
    expect(container).toHaveClass('justify-start');
  });

  it('displays sub-agent name when present', () => {
    const message = createAIMessage({
      sub_agent_name: 'SpecializedAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('SpecializedAgent')).toBeInTheDocument();
  });
});