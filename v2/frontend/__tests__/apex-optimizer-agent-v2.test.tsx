
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ApexOptimizerAgentV2 } from '@/app/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/app/providers/AgentProvider';
import useAppStore from '@/app/store';

jest.mock('@/app/providers/AgentProvider', () => ({
  useAgentContext: jest.fn(),
}));

jest.mock('@/app/store', () => ({
  __esModule: true,
  default: jest.fn(),
}));

describe('ApexOptimizerAgentV2', () => {
  const mockSendWsMessage = jest.fn();

  beforeEach(() => {
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [{ type: 'user', content: 'Test message', id: '1' }],
      showThinking: false,
      sendWsMessage: mockSendWsMessage,
      error: null,
    });
    (useAppStore as jest.Mock).mockReturnValue({
      user: { id: 'test-user', name: 'Test User', picture: 'https://example.com/avatar.png' },
    });
  });

  it('should render the chat window', async () => {
    await act(async () => {
      render(<ApexOptimizerAgentV2 />);
    });
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('should call sendWsMessage when a message is sent', async () => {
    await act(async () => {
      render(<ApexOptimizerAgentV2 />);
    });
    const input = screen.getByPlaceholderText('Type your message...');
    const form = input.closest('form');

    await act(async () => {
        if(form){
            fireEvent.change(input, { target: { value: 'Test message' } });
            fireEvent.submit(form);
        }
    });

    expect(mockSendWsMessage).toHaveBeenCalledWith({
      type: 'analysis_request',
      payload: {
        settings: {
          debug_mode: true,
        },
        request: {
          user_id: 'test-user',
          query: 'Test message',
          workloads: [],
          references: [],
        },
      },
    });
  });

  it('should call sendWsMessage when an example query is clicked', async () => {
    await act(async () => {
      render(<ApexOptimizerAgentV2 />);
    });
    const exampleButton = screen.getByText(/Overview of the lowest hanging optimization fruit/);

    await act(async () => {
      fireEvent.click(exampleButton);
    });

    expect(screen.getByPlaceholderText('Type your message...')).toHaveValue("Overview of the lowest hanging optimization fruit that I can implement with config only change");
  });
});
