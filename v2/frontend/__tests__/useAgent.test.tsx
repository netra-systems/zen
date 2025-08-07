import { renderHook, waitFor, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import WS from 'jest-websocket-mock';
import { getToken, getUserId } from '../app/lib/user';

jest.mock('../app/lib/user', () => ({
  getToken: jest.fn(),
  getUserId: jest.fn(),
}));

describe('useAgent', () => {
  let server: WS;

  beforeEach(() => {
    (getToken as jest.Mock).mockResolvedValue('test-token');
    (getUserId as jest.Mock).mockReturnValue('test-user');
    const url = 'ws://localhost:8000/ws/test-user';
    server = new WS(url, { jsonProtocol: true });
  });

  afterEach(() => {
    WS.clean();
    jest.restoreAllMocks();
  });

  it('should connect, send a message, and process the response', async () => {
    const { result } = renderHook(() => useAgent('test-user'));

    await server.connected;

    act(() => {
      result.current.sendMessage('Test message');
    });

    const streamEvent = {
        event: 'update_state',
        data: { todo_list: ['Step 1'], completed_steps: [] },
    };

    server.send(JSON.stringify(streamEvent));

    await waitFor(() => {
        const lastMessage = result.current.messages[result.current.messages.length - 1];
        expect(lastMessage.state).toBeDefined();
        if(lastMessage.state) {
            expect(lastMessage.state.todo_list).toEqual(['Step 1']);
        }
    });

  }, 20000);
});