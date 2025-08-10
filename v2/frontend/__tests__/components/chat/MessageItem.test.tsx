
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';
import { Message } from '@/types/chat';

describe('MessageItem', () => {
  it('renders a user message correctly', () => {
    const message: Message = {
      id: '1',
      type: 'user',
      content: 'Hello, world!',
      sub_agent_name: 'User',
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    expect(screen.getByText('User')).toBeInTheDocument();
  });

  it('renders an agent message correctly', () => {
    const message: Message = {
      id: '2',
      type: 'agent',
      content: 'Hi there!',
      sub_agent_name: 'Test Agent',
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
  });

  it('renders an error message correctly', () => {
    const message: Message = {
      id: '3',
      type: 'agent',
      content: '',
      sub_agent_name: 'Test Agent',
      error: 'Something went wrong',
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders tool info correctly', () => {
    const message: Message = {
      id: '4',
      type: 'agent',
      content: '',
      sub_agent_name: 'Test Agent',
      tool_info: { tool: 'test_tool', args: [1, 2] },
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Tool Information')).toBeInTheDocument();
  });
});
