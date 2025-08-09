import { render, screen, fireEvent } from '@testing-library/react';
import { ApexOptimizerAgentV2 } from '@/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/contexts/AgentContext';
import { useAuth } from '@/hooks/useAuth';
import { authService } from '@/services/auth';
import { mockUser } from '@/mocks/auth';

jest.mock('@/hooks/useAuth');
jest.mock('@/contexts/AgentContext');
jest.mock('@/services/auth');

describe('ApexOptimizerAgentV2', () => {
  const sendWsMessage = jest.fn();

  beforeEach(() => {
    (useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      loading: false,
    });
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ user: mockUser });
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [{ type: 'user', content: 'Test message', id: '1' }],
      showThinking: false,
      sendWsMessage,
      subAgentName: 'Test Agent',
      subAgentStatus: 'Test Status',
      exampleQueries: ['Example 1', 'Example 2'],
    });
  });

  it('should render the chat window', () => {
    render(<ApexOptimizerAgentV2 />);
    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('Test Status')).toBeInTheDocument();
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('should call sendWsMessage when a message is sent', () => {
    render(<ApexOptimizerAgentV2 />);
    const input = screen.getByPlaceholderText('Ask a question or type a command...');
    fireEvent.change(input, { target: { value: 'New message' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(sendWsMessage).toHaveBeenCalledWith('New message');
  });

  it('should call sendWsMessage when an example query is clicked', () => {
    render(<ApexOptimizerAgentV2 />);
    fireEvent.click(screen.getByText('Example 1'));
    expect(sendWsMessage).toHaveBeenCalledWith('Example 1');
  });
});