import { renderHook, waitFor, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import WS from 'jest-websocket-mock';

describe('useAgent', () => {
  let server: WS;
  const userId = 'test-user';
  const wsUrl = `ws://localhost:8000/ws/${userId}`;

  beforeEach(() => {
    server = new WS(wsUrl, { jsonProtocol: true });
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect, send a message, and process the response', async () => {
    const { result } = renderHook(() => useAgent(userId));

    await server.connected;

    act(() => {
      result.current.sendMessage('Test message');
    });

    const streamEvent = {
        event: 'update_state',
        data: { todo_list: ['Step 1'], completed_steps: [] },
    };

    await act(async () => {
        server.send(JSON.stringify(streamEvent));
    });

    await waitFor(() => {
        const lastMessage = result.current.messages[result.current.messages.length - 1];
        expect(lastMessage.state).toBeDefined();
        if(lastMessage.state) {
            expect(lastMessage.state.todo_list).toEqual(['Step 1']);
        }
    });

  }, 20000);
});