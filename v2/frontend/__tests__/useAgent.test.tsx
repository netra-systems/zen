import { renderHook, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import { server, mockSocket } from '../mocks/server';
import { getToken } from '../app/lib/user';

// Mock the user module
jest.mock('../app/lib/user', () => ({
  getUserId: jest.fn(() => 'test-user'),
  getToken: jest.fn(() => Promise.resolve('test-token')),
}));

describe('useAgent', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('should start the agent, show thinking indicator, and process the response', async () => {
    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('test message');
    });

    expect(result.current.showThinking).toBe(true);

    act(() => {
      mockSocket.onmessage!(
        new MessageEvent('message', {
          data: JSON.stringify({
            event: 'on_chain_start',
            run_id: 'run_123',
            data: { input: { todo_list: ['step 1'] } },
          }),
        }),
      );
    });

    expect(result.current.messages).toHaveLength(2); // User message + agent thinking message
    expect(result.current.messages[1].state_updates.todo_list).toEqual(['step 1']);

    act(() => {
      mockSocket.onmessage!(
        new MessageEvent('message', {
          data: JSON.stringify({ event: 'run_complete' }),
        }),
      );
    });

    expect(result.current.showThinking).toBe(false);
  });

  it('should handle errors when calling the agent', async () => {
    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('test message');
    });

    act(() => {
        mockSocket.onerror!(new Event('error'));
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.showThinking).toBe(false);
  });

  it('should not start the agent if no token is available', async () => {
    (getToken as jest.Mock).mockResolvedValueOnce(null);

    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('test message');
    });

    expect(result.current.error).not.toBeNull();
    expect(result.current.showThinking).toBe(false);
  });
});