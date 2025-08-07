import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MessageCard } from '../MessageCard';
import { ArtifactMessage, Message } from '@/app/types/chat';

const mockUser = {
  name: 'Test User',
  picture: 'test.jpg',
};

describe('MessageCard', () => {
  it('renders a thinking message', () => {
    const message: Message = {
      id: '1',
      role: 'agent',
      timestamp: new Date().toISOString(),
      type: 'thinking',
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByTestId('thinking-indicator')).toBeInTheDocument();
  });

  it('renders a user message', () => {
    const message: Message = {
      id: '2',
      role: 'user',
      timestamp: new Date().toISOString(),
      type: 'text',
      content: 'Hello, world!',
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('renders an artifact message with a tool name', () => {
    const message: ArtifactMessage = {
      id: '3',
      role: 'agent',
      timestamp: new Date().toISOString(),
      type: 'artifact',
      name: 'on_tool_start',
      data: {},
      tool_calls: [{ name: 'test_tool', args: {}, id: 'tool1', type: 'tool_call' }],
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByText(/Tool: test_tool/)).toBeInTheDocument();
  });

  it('renders an artifact message with a todo list', () => {
    const message: ArtifactMessage = {
      id: '4',
      role: 'agent',
      timestamp: new Date().toISOString(),
      type: 'artifact',
      name: 'on_chain_start',
      data: {},
      state_updates: {
        todo_list: ['step 1', 'step 2'],
        completed_steps: ['step 0'],
      },
    };
    render(<MessageCard message={message} user={mockUser} />);
    fireEvent.click(screen.getByText('TODO List'));
    expect(screen.getByText('step 1')).toBeInTheDocument();
    expect(screen.getByText('step 2')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Completed Steps'));
    expect(screen.getByText('step 0')).toBeInTheDocument();
  });

  it('renders an artifact message with errors', () => {
    const message: ArtifactMessage = {
      id: '5',
      role: 'agent',
      timestamp: new Date().toISOString(),
      type: 'artifact',
      name: 'on_tool_end',
      data: {},
      tool_outputs: [{ tool_call_id: 'tool1', content: 'Error message', is_error: true }],
    };
    render(<MessageCard message={message} user={mockUser} />);
    fireEvent.click(screen.getByText('Errors:').parentElement as HTMLElement);
    expect(screen.getByText('Error message')).toBeInTheDocument();
  });
});