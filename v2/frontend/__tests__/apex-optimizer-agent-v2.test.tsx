import { render, screen, fireEvent, act } from '@testing-library/react';
import { ApexOptimizerAgentV2 } from '@/components/apex-optimizer-agent-v2';
import { AgentProvider, useAgentContext } from '@/contexts/AgentContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { useAuth } from '@/hooks/useAuth';
import * as auth from '@/services/auth';
import { mockUser } from '@/mocks/auth';

jest.mock('@/hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/services/auth');

jest.mock('@/contexts/AgentContext', () => ({
  ...jest.requireActual('@/contexts/AgentContext'),
  useAgentContext: jest.fn(),
}));

const mockGetAuthConfig = auth.getAuthConfig as jest.Mock;

describe('ApexOptimizerAgentV2', () => {
  const mockSendWsMessage = jest.fn();

  beforeEach(() => {
    (useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
    });
    mockGetAuthConfig.mockResolvedValue({ user: mockUser });
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [{ type: 'user', content: 'Test message', id: '1' }],
      showThinking: false,
      sendWsMessage: mockSendWsMessage,
      error: null,
    });
  });

  it('should render the chat window', async () => {
    await act(async () => {
      render(
        <AuthProvider>
          <AgentProvider>
            <ApexOptimizerAgentV2 />
          </AgentProvider>
        </AuthProvider>
      );
    });
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  it('should call sendWsMessage when a message is sent', async () => {
    await act(async () => {
      render(
        <AuthProvider>
          <AgentProvider>
            <ApexOptimizerAgentV2 />
          </AgentProvider>
        </AuthProvider>
      );
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
          user_id: mockUser.id,
          query: 'Test message',
          workloads: [],
          references: [],
        },
      },
    });
  });

  it('should call sendWsMessage when an example query is clicked', async () => {
    await act(async () => {
      render(
        <AuthProvider>
          <AgentProvider>
            <ApexOptimizerAgentV2 />
          </AgentProvider>
        </AuthProvider>
      );
    });
    const exampleButton = screen.getByText(/Overview of the lowest hanging optimization fruit/);

    await act(async () => {
      fireEvent.click(exampleButton);
    });

    expect(screen.getByPlaceholderText('Type your message...')).toHaveValue("Overview of the lowest hanging optimization fruit that I can implement with config only change");
  });
});
