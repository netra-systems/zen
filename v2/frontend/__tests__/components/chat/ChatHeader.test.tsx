
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
      subAgentStatus: { lifecycle: 'running' },
      isProcessing: false,
    });
    render(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('should render default status when no status provided', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: 'Test Agent',
      subAgentStatus: { lifecycle: null },
      isProcessing: false,
    });
    render(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
  });

  it('should render default agent name when no name provided', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: null,
      subAgentStatus: null,
      isProcessing: false,
    });
    render(<ChatHeader />);
    expect(screen.getByText('Netra AI Agent')).toBeInTheDocument();
  });

  it('should render processing state', () => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: 'Test Agent',
      subAgentStatus: { lifecycle: 'active' },
      isProcessing: true,
    });
    render(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
  });
});
