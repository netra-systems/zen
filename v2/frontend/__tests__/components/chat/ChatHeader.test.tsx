
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { useChatStore } from '@/store/chat';

// Mock the useChatStore hook
jest.mock('@/store/chat', () => ({
  useChatStore: jest.fn(),
}));

describe('ChatHeader', () => {
  it('should render the sub-agent name and status', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: 'Test Agent',
      subAgentStatus: { status: 'running', tools: [] },
    });
    render(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('should render the tools being used', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: 'Test Agent',
      subAgentStatus: { status: 'running', tools: ['tool1', 'tool2'] },
    });
    render(<ChatHeader />);
    expect(screen.getByText('Tools: tool1, tool2')).toBeInTheDocument();
  });
});
