import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../app/hooks/useWebSocket';
import WS from 'jest-websocket-mock';

describe('useWebSocket', () => {
  let server: WS;

  beforeEach(async () => {
    server = new WS('ws://localhost:8000/ws/123');
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect, handshake, and handle JSON messages', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await server.connected;

    await waitFor(() => expect(result.current.isConnected).toBe(true));

    act(() => {
      server.send('handshake_ack');
    });

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
        server.send(JSON.stringify(testMessage));
    });

    await waitFor(() => expect(result.current.messages).toEqual([testMessage]));
  });
});