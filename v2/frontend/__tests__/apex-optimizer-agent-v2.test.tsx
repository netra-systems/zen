
import { render, screen, fireEvent } from '@testing-library/react';
import ApexOptimizerAgentV2 from '@/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/providers/AgentProvider';
import { UserProvider } from '@/providers/UserProvider';

jest.mock('@/providers/AgentProvider', () => ({
  useAgentContext: jest.fn(),
}));

jest.mock('@/providers/UserProvider', () => ({
  useUser: () => ({ user: { id: 'test-user' }, isLoading: false }),
  UserProvider: ({ children }) => <div>{children}</div>,
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
  });

  it('should render the chat window', () => {
    render(
      <UserProvider>
        <ApexOptimizerAgentV2 />
      </UserProvider>
    );
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('should call startAgent when a message is sent', () => {
    render(
      <UserProvider>
        <ApexOptimizerAgentV2 />
      </UserProvider>
    );
    const input = screen.getByPlaceholderText('Ask the agent to optimize a tool...');
    const sendButton = screen.getByText('Send');

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.submit(screen.getByRole('form'));

    expect(mockStartAgent).toHaveBeenCalledWith('Test message');
  });

  it('should call startAgent when an example query is clicked', () => {
    render(
      <UserProvider>
        <ApexOptimizerAgentV2 />
      </UserProvider>
    );
    const exampleButton = screen.getByText(/Analyze the latency/);

    fireEvent.click(exampleButton);

    expect(screen.getByRole('textbox')).toHaveValue("Analyze the latency of the `get_user_data` tool and suggest optimizations.");
  });
});
