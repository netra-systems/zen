
import { render, screen, fireEvent } from '@testing-library/react';
import ApexOptimizerAgentV2 from '@/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/app/providers/AgentProvider';

jest.mock('@/providers/AgentProvider');

describe('ApexOptimizerAgentV2', () => {
  const mockStartAgent = jest.fn();

  beforeEach(() => {
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [],
      showThinking: false,
      startAgent: mockStartAgent,
      error: null,
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
    const exampleButton = screen.getByText(/Overview of the lowest hanging optimization fruit/);

    fireEvent.click(exampleButton);

    expect(screen.getByRole('textbox')).toHaveValue("Overview of the lowest hanging optimization fruit that I can implement with config only change");
  });
});
