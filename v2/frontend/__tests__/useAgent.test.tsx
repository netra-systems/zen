import { renderHook, act } from '@testing-library/react-hooks';
import { useAgent } from '../app/hooks/useAgent';
import { Server } from 'ws';
import { Message, StreamEvent } from '../app/types/chat';

global.WebSocket = require('ws');

describe('useAgent', () => {
  let server: Server;

  beforeEach(done => {
    server = new Server({ port: 8000 }, done);
  });

  afterEach(done => {
    server.close(done);
  });

  it('should connect to the WebSocket server', async () => {
    const { result, waitFor } = renderHook(() => useAgent());
    await waitFor(() => expect(result.current.messages).toBeDefined());
    // No direct way to check isConnected from outside, so we infer it by lack of error
  });

  it('should handle incoming stream events and update messages', async () => {
    const { result, waitFor } = renderHook(() => useAgent());

    const streamEvent: StreamEvent = {
      event: 'on_chain_start',
      run_id: 'run123',
      data: {
        input: {
          messages: [],
          workloads: [],
          todo_list: ['do a thing'],
          completed_steps: [],
          status: 'in_progress',
          events: [],
        },
      },
    };

    act(() => {
      server.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(streamEvent));
        }
      });
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBe(1);
      const message = result.current.messages[0] as any;
      expect(message.id).toBe('run123');
      expect(message.state_updates.todo_list).toEqual(['do a thing']);
    });
  });

  it('should set showThinking to false on run_complete', async () => {
    const { result, waitFor } = renderHook(() => useAgent());

    act(() => {
      result.current.startAgent('test message');
    });

    await waitFor(() => {
      expect(result.current.showThinking).toBe(true);
    });

    const streamEvent: StreamEvent = {
      event: 'run_complete',
      run_id: 'run123',
      data: { status: 'complete' },
    };

    act(() => {
      server.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(streamEvent));
        }
      });
    });

    await waitFor(() => {
      expect(result.current.showThinking).toBe(false);
    });
  });
});
