import { render, screen, fireEvent } from '@testing-library/react';
import { MessageCard } from '../MessageCard';
import { Message } from '../../../types/chat';

const mockUser = {
  name: 'Test User',
  picture: 'https://example.com/avatar.png',
};

describe('MessageCard', () => {
  it('renders a thinking message', () => {
    const message: Message = {
      id: '1',
      role: 'assistant',
      type: 'thinking',
      content: '',
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByText('Thinking...')).toBeInTheDocument();
  });

  it('renders a user message', () => {
    const message: Message = {
      id: '2',
      role: 'user',
      type: 'text',
      content: 'Hello, world!',
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByText('Hello, world!')).toBeInTheDocument();
  });

  it('renders a tool start message', () => {
    const message: Message = {
      id: '3',
      role: 'assistant',
      type: 'tool_start',
      content: '',
      tool: 'test_tool',
      toolInput: { key: 'value' },
    };
    render(<MessageCard message={message} user={mockUser} />);
    fireEvent.click(screen.getByText('Raw Message'));
    const accordion = screen.getByRole('region');
    expect(accordion).toBeInTheDocument();
    expect(screen.getAllByText(/key/).length).toBe(2);
    expect(screen.getAllByText(/value/).length).toBe(2);
  });

  it('renders a state update message with a todo list', () => {
    const message: Message = {
      id: '4',
      role: 'assistant',
      type: 'state_update',
      content: '',
      state: {
        todo_list: ['step 1', 'step 2'],
        completed_steps: ['step 0'],
      },
    };
    render(<MessageCard message={message} user={mockUser} />);
    expect(screen.getByText('step 1')).toBeInTheDocument();
    expect(screen.getByText('step 2')).toBeInTheDocument();
  });

  it('renders a tool end message with errors', () => {
    const message: Message = {
      id: '5',
      role: 'assistant',
      type: 'tool_end',
      content: '',
      toolOutput: {
        content: 'Error message',
        is_error: true,
      },
    };
    render(<MessageCard message={message} user={mockUser} />);
    fireEvent.click(screen.getByText('Raw Message'));
    const accordion = screen.getByRole('region');
    expect(accordion).toBeInTheDocument();
    expect(screen.getAllByText(/Error message/).length).toBe(2);
  });
});