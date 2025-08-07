import { renderHook, waitFor, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import WS from 'jest-websocket-mock';
import { getToken, getUserId } from '../app/lib/user';
import { WebSocketStatus } from '../app/hooks/useWebSocket';

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
    jest.restoreAllMocks();
  });

  it('should connect on first load, start the agent, show thinking indicator, and process the response', async () => {
    const mockDateNow = jest.spyOn(Date, 'now').mockImplementation(() => 12345);
    const runId = `run_${Date.now()}`;
    const url = `ws://localhost:8000/agent/${runId}?token=test-token`;
    server = new WS(url, { jsonProtocol: true });

    const { result } = renderHook(() => useAgent());

    await waitFor(() => expect(result.current.status).toBe(WebSocketStatus.Open));

    act(() => {
      result.current.startAgent('Test message');
    });

    await waitFor(() => expect(result.current.showThinking).toBe(true));

    const streamEvent = {
        event: 'on_chain_start',
        data: { input: { todo_list: ['Step 1'], completed_steps: [] } },
        run_id: runId,
    };

    server.send(streamEvent);

    await waitFor(() => {
        expect(result.current.messages).toHaveLength(2);
        expect(result.current.messages[1].type).toBe('artifact');
    });

    server.send({ event: 'run_complete', run_id: runId });

    await waitFor(() => expect(result.current.showThinking).toBe(false));

  }, 20000);
});