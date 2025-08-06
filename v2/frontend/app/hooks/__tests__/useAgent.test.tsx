import { renderHook, act } from '@testing-library/react-hooks';
import { useAgent } from '../useAgent';
import { getToken } from '../../lib/user';

jest.mock('../../lib/user', () => ({
  getToken: jest.fn(),
}));

global.fetch = jest.fn();

describe('useAgent', () => {
  beforeEach(() => {
    (getToken as jest.Mock).mockResolvedValue('test-token');
    (global.fetch as jest.Mock).mockClear();
  });

  it('should start the agent, show thinking indicator, and process the response', async () => {
    const mockStream = new ReadableStream({
      start(controller) {
        controller.enqueue('event: on_chat_model_stream\n');
        controller.enqueue('data: { \"chunk\": { \"content\": \"Hello\" } }\n\n');
        controller.enqueue('event: on_chain_end\n');
        controller.enqueue('data: {}\n\n');
        controller.close();
      },
    });
    (global.fetch as jest.Mock).mockResolvedValue({ body: mockStream });

    const { result, waitForNextUpdate } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('Test message');
      await waitForNextUpdate();
    });

    expect(result.current.showThinking).toBe(true);

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    expect(result.current.messages).toEqual([
      { id: expect.any(String), role: 'user', timestamp: expect.any(String), type: 'text', content: 'Test message' },
      { id: expect.any(String), role: 'agent', timestamp: expect.any(String), type: 'thinking', content: 'Hello' },
    ]);

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    expect(result.current.showThinking).toBe(false);
  });

  it('should handle errors when calling the agent', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('API Error'));

    const { result, waitForNextUpdate } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('Test message');
      await waitForNextUpdate();
    });

    expect(result.current.showThinking).toBe(true);

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });

    expect(result.current.showThinking).toBe(false);
  });

  it('should not start the agent if no token is available', async () => {
    (getToken as jest.Mock).mockResolvedValue(null);

    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('Test message');
    });

    expect(fetch).not.toHaveBeenCalled();
  });
});
