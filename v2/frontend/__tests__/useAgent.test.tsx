import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import WS from 'jest-websocket-mock';

describe('useAgent', () => {
  let server: WS;

  beforeEach(async () => {
    server = new WS('ws://localhost:8000/agent/run_123?token=test-token', { jsonProtocol: true });
  });

  afterEach(() => {
    WS.clean();
  });

  it('should start the agent, show thinking indicator, and process the response', async () => {
    const { result } = renderHook(() => useAgent());

    act(() => {
        result.current.startAgent('Test message');
    });

    await server.connected;

    await waitFor(() => expect(result.current.showThinking).toBe(true));

    const streamEvent = {
        event: 'on_chain_start',
        data: { input: { todo_list: ['Step 1'], completed_steps: [] } },
        run_id: 'run_123',
    };

    act(() => {
        server.send(streamEvent);
    });

    await waitFor(() => {
        expect(result.current.messages).toHaveLength(2);
        expect(result.current.messages[1].type).toBe('artifact');
    });

    act(() => {
        server.send({ event: 'run_complete', run_id: 'run_123' });
    });

    await waitFor(() => expect(result.current.showThinking).toBe(false));
  });
});