import { render, screen } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { useChatStore } from '@/store';

jest.mock('@/store');

describe('ChatHeader', () => {
  beforeEach(() => {
    (useChatStore as jest.Mock).mockReturnValue({
      subAgentName: 'Test Agent',
      subAgentStatus: {
        status: 'running',
        tools: ['tool1', 'tool2'],
      },
    });
  });

  it('should render the sub-agent name and status', () => {
    render(<ChatHeader />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('should render the tools being used', () => {
    render(<ChatHeader />);
    expect(screen.getByText('Tools: tool1, tool2')).toBeInTheDocument();
  });
});