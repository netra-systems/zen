import { render, screen } from '@testing-library/react';
import { authService } from '@/auth';
import { ApexOptimizerAgentV2 } from '@/components/apex-optimizer-agent-v2';
import { useAgentContext } from '@/contexts/AgentContext';
import { mockUser } from '@/mocks/auth';


jest.mock('@/contexts/AgentContext');
jest.mock('@/services/auth');

describe('ApexOptimizerAgentV2', () => {
  const sendWsMessage = jest.fn();

  beforeEach(() => {
    (authService.useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      loading: false,
    });
    
    (useAgentContext as jest.Mock).mockReturnValue({
      messages: [{ type: 'user', content: 'Test message', id: '1', created_at: new Date().toISOString() }],
      showThinking: false,
      sendWsMessage,
      subAgentName: 'Test Agent',
      subAgentStatus: 'Test Status',
      exampleQueries: ['Example 1', 'Example 2'],
      error: null,
    });
  });

  it('should render the chat window', () => {
    render(<ApexOptimizerAgentV2 />);
    expect(screen.getByText('Apex Optimizer Agent')).toBeInTheDocument();
  });
});