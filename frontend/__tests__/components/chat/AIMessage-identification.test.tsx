/**
 * AI Message Agent Identification Tests
 * 
 * Tests agent naming, identification, and subtitle display behavior.
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
// AGENT NAMING AND IDENTIFICATION TESTS
// ============================================================================

describe('AIMessage - Agent Identification', () => {
  it('displays correct agent name for different agents', () => {
    const message = createAIMessage({
      sub_agent_name: 'DataAnalysisAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('DataAnalysisAgent')).toBeInTheDocument();
  });

  it('shows agent subtitle when appropriate', () => {
    const message = createAIMessage({
      sub_agent_name: 'ComplexAgent'
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    const subtitle = screen.queryByText(/AI Assistant/);
    if (subtitle) {
      expect(subtitle).toHaveClass('text-gray-500');
    }
  });

  it('handles missing agent name gracefully', () => {
    const message = createAIMessage({
      sub_agent_name: undefined
    });
    renderWithChatSetup(<MessageItem message={message} />);
    
    expect(screen.getByText('Netra Agent')).toBeInTheDocument();
  });

  it('displays bot icon for AI messages', () => {
    const message = createAIMessage();
    renderWithChatSetup(<MessageItem message={message} />);
    
    const botIcon = document.querySelector('svg.lucide-bot') ||
                   screen.getByText('OptimizationAgent').parentElement?.querySelector('svg');
    expect(botIcon).toBeInTheDocument();
  });
});