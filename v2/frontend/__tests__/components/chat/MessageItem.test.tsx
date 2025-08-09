import { render, screen } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';

describe('MessageItem', () => {
  it('should render a user message with content', () => {
    const message = {
      id: '1',
      created_at: new Date().toISOString(),
      content: 'Hello, agent!',
      type: 'user',
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Hello, agent!')).toBeInTheDocument();
    expect(screen.getByText('U')).toBeInTheDocument(); // User avatar fallback
  });

  it('should render an agent message with content', () => {
    const message = {
      id: '2',
      created_at: new Date().toISOString(),
      content: 'Hello, user!',
      type: 'agent',
      sub_agent_name: 'TestAgent',
      displayed_to_user: true,
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Hello, user!')).toBeInTheDocument();
    expect(screen.getByText('TestAgent')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument(); // Agent avatar fallback
  });

  it('should render user message with references', () => {
    const message = {
      id: '3',
      created_at: new Date().toISOString(),
      content: 'Message with references',
      type: 'user',
      displayed_to_user: true,
      references: ['ref1', 'ref2'],
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('Message with references')).toBeInTheDocument();
    expect(screen.getByText('References:')).toBeInTheDocument();
    expect(screen.getByText('ref1')).toBeInTheDocument();
    expect(screen.getByText('ref2')).toBeInTheDocument();
  });

  it('should render raw data when available', () => {
    const message = {
      id: '4',
      created_at: new Date().toISOString(),
      content: 'Message with raw data',
      type: 'system',
      displayed_to_user: true,
      raw_data: { key: 'value' },
    };
    render(<MessageItem message={message} />);
    expect(screen.getByText('View Raw Data')).toBeInTheDocument();
  });
});