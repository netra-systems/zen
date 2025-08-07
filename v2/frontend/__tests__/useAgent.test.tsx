import { renderHook, act, waitFor } from '@testing-library/react';
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
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect on first load, start the agent, show thinking indicator, and process the response', async () => {
    const { result } = renderHook(() => useAgent());

    // The hook connects automatically, so we need to wait for the server to be created.
    // We can get the URL from the mock WebSocket constructor.
    const url = (WS as any).instances[0].url;
    server = new WS(url, { jsonProtocol: true });

    await server.connected;

    act(() => {
        result.current.startAgent('Test message');
    });

    await waitFor(() => expect(result.current.showThinking).toBe(true));

    const runId = url.split('/').pop().split('?')[0];

    const streamEvent = {
        event: 'on_chain_start',
        data: { input: { todo_list: ['Step 1'], completed_steps: [] } },
        run_id: runId,
    };

    act(() => {
        server.send(streamEvent);
    });

    await waitFor(() => {
        expect(result.current.messages).toHaveLength(2); // user message + artifact
        expect(result.current.messages[1].type).toBe('artifact');
    });

    act(() => {
        server.send({ event: 'run_complete', run_id: runId });
    });

    await waitFor(() => expect(result.current.showThinking).toBe(false));
  }, 10000);
});