
import React from 'react';
import { render, screen } from '@testing-library/react';
import { AgentMessageCard } from '../AgentMessageCard';
import { AgentMessage } from '@/types';

describe('AgentMessageCard', () => {
  const mockMessage: AgentMessage = {
    id: '1',
    role: 'agent',
    type: 'agent',
    subAgentName: 'Test Agent',
    content: 'This is a test message',
    tools: [
      {
        name: 'Test Tool',
        input: { param1: 'value1' },
        output: { result: 'success' },
      },
    ],
    todos: [
      {
        description: 'Test Todo',
        state: 'pending',
      },
    ],
    toolErrors: ['Test Error'],
  };

  it('renders the sub-agent name', () => {
    render(<AgentMessageCard message={mockMessage} />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  it('renders the message content', () => {
    render(<AgentMessageCard message={mockMessage} />);
    expect(screen.getByText('This is a test message')).toBeInTheDocument();
  });

  it('renders the tools used', () => {
    render(<AgentMessageCard message={mockMessage} />);
    expect(screen.getByText('Tools Used')).toBeInTheDocument();
    expect(screen.getByText('Test Tool')).toBeInTheDocument();
  });

  it('renders the todo list', () => {
    render(<AgentMessageCard message={mockMessage} />);
    expect(screen.getByText('TODO List')).toBeInTheDocument();
  });

  it('renders the tool errors', () => {
    render(<AgentMessageCard message={mockMessage} />);
    expect(screen.getByText('Tool Errors:')).toBeInTheDocument();
    expect(screen.getByText('Test Error')).toBeInTheDocument();
  });
});
