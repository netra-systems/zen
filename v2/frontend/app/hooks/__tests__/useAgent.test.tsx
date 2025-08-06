import { render, screen, act } from '@testing-library/react';
import { useAgent } from '../useAgent';
import { getToken } from '../../lib/user';
import { FC, useEffect } from 'react';

jest.mock('../../lib/user', () => ({
  getToken: jest.fn(),
}));

const mockFetch = jest.fn();
global.fetch = mockFetch;

const TestComponent: FC<{ message: string }> = ({ message }) => {
  const { startAgent, messages, showThinking } = useAgent();

  useEffect(() => {
    if (message) {
      startAgent(message);
    }
  }, [message, startAgent]);

  return (
    <div>
      {showThinking && <div>Thinking...</div>}
      <ul>
        {messages.map((msg) => (
          <li key={msg.id}>{msg.content}</li>
        ))}
      </ul>
    </div>
  );
};

describe('useAgent', () => {
  beforeEach(() => {
    (getToken as jest.Mock).mockResolvedValue('test-token');
    mockFetch.mockClear();
  });

  it('should start the agent, show thinking indicator, and process the response', async () => {
    const mockStream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode('event: on_chat_model_stream\n'));
        controller.enqueue(encoder.encode('data: { \"chunk\": { \"content\": \"Hello\" } }\n\n'));
        controller.enqueue(encoder.encode('event: on_chain_end\n'));
        controller.enqueue(encoder.encode('data: {}\n\n'));
        controller.close();
      },
    });
    mockFetch.mockResolvedValue({ body: mockStream });

    render(<TestComponent message="Test message" />);

    expect(screen.getByText('Thinking...')).toBeInTheDocument();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.getByText('Test message')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.queryByText('Thinking...')).not.toBeInTheDocument();
  });

  it('should handle errors when calling the agent', async () => {
    mockFetch.mockRejectedValue(new Error('API Error'));

    render(<TestComponent message="Test message" />);

    expect(screen.getByText('Thinking...')).toBeInTheDocument();

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(screen.queryByText('Thinking...')).not.toBeInTheDocument();
  });

  it('should not start the agent if no token is available', async () => {
    (getToken as jest.Mock).mockResolvedValue(null);

    render(<TestComponent message="Test message" />);

    expect(mockFetch).not.toHaveBeenCalled();
  });
});
