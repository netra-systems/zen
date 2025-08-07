import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import { getToken } from '../app/lib/user';
import WS from 'jest-websocket-mock';

// Mock the user module
jest.mock('../app/lib/user', () => ({
  getUserId: jest.fn(() => 'test-user'),
  getToken: jest.fn(() => Promise.resolve('test-token')),
}));

describe('useAgent', () => {
  let server: WS;

  beforeEach(async () => {
    server = new WS('ws://localhost:8000/agent/run_123?token=test-token');
  });

  afterEach(() => {
    WS.clean();
  });

  it('should start the agent, show thinking indicator, and process the response', async () => {
    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('test message');
    });

    await server.connected;

    expect(result.current.showThinking).toBe(true);

    act(() => {
      server.send(JSON.stringify({
        event: 'on_chain_start',
        run_id: result.current.messages[0].id,
        data: { input: { todo_list: ['step 1'] } },
      }));
    });

    await waitFor(() => {
        expect(result.current.messages.length).toBe(2);
        expect(result.current.messages[1].state_updates.todo_list).toEqual(['step 1']);
    });

    act(() => {
      server.send(JSON.stringify({ event: 'run_complete' }));
    });

    await waitFor(() => expect(result.current.showThinking).toBe(false));
  });

  it('should handle errors when calling the agent', async () => {
    const { result } = renderHook(() => useAgent());

    await act(async () => {
      result.current.startAgent('test message');
    });
    
    await server.connected;

    act(() => {
        server.error();
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());
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
