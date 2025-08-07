
import { render, screen, fireEvent } from '@testing-library/react';
import ApexOptimizerAgentV2 from '@/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/providers/AgentProvider';
import useAuth from '@/auth';

jest.mock('@/providers/AgentProvider', () => ({
  useAgentContext: jest.fn(),
}));

jest.mock('@/auth', () => ({
  __esModule: true,
  default: jest.fn(),
}));

describe('ApexOptimizerAgentV2', () => {
  const mockStartAgent = jest.fn();

  beforeEach(() => {
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [{ type: 'human', content: 'Test message' }],
      showThinking: false,
      startAgent: mockStartAgent,
      error: null,
    });
    (useAuth as jest.Mock).mockReturnValue({
      user: { id: 'test-user', name: 'Test User', picture: '' },
      login: jest.fn(),
      logout: jest.fn(),
    });
  });

  it('should render the chat window', () => {
    render(<ApexOptimizerAgentV2 />);
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('should call startAgent when a message is sent', () => {
    render(<ApexOptimizerAgentV2 />);
    const input = screen.getByPlaceholderText('Ask the agent to optimize a tool...');
    const sendButton = screen.getByText('Send');

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.submit(screen.getByRole('form'));

    expect(mockStartAgent).toHaveBeenCalledWith('Test message');
  });

  it('should call startAgent when an example query is clicked', () => {
    render(<ApexOptimizerAgentV2 />);
    const exampleButton = screen.getByText(/Analyze the latency/);

    fireEvent.click(exampleButton);

    expect(screen.getByRole('textbox')).toHaveValue("Analyze the latency of the `get_user_data` tool and suggest optimizations.");
  });
});
