
import React from 'react';
import { render, screen } from '@testing-library/react';
import { UserMessageCard } from '@/components/chat/UserMessageCard';
import { UserMessage } from '@/types';

describe('UserMessageCard', () => {
  const mockMessage: UserMessage = {
    id: '1',
    role: 'user',
    type: 'user',
    content: 'This is a test message',
    references: [
      {
        id: '1',
        name: 'Test Reference',
        friendly_name: 'Test Reference',
        description: 'This is a test reference',
        type: 'test',
        value: 'test',
        version: '1',
      },
    ],
  };

  it('renders the message content', () => {
    render(<UserMessageCard message={mockMessage} />);
    expect(screen.getByText('This is a test message')).toBeInTheDocument();
  });

  it('renders the references', () => {
    render(<UserMessageCard message={mockMessage} />);
    expect(screen.getByText('References:')).toBeInTheDocument();
    expect(screen.getByText('Test Reference')).toBeInTheDocument();
  });
});
