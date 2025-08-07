
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket, WebSocketStatus } from '../app/hooks/useWebSocket';
import WS from 'jest-websocket-mock';

describe('useWebSocket', () => {
  let server: WS;

  beforeEach(async () => {
    server = new WS('ws://localhost:8000/ws/123');
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect and change status to Open', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await server.connected;

    await waitFor(() => expect(result.current.status).toBe(WebSocketStatus.Open));
  });

  it('should receive messages', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await server.connected;

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
        server.send(JSON.stringify(testMessage));
    });

    await waitFor(() => expect(JSON.parse(result.current.lastMessage!.data)).toEqual(testMessage));
  });

  it('should send messages', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await server.connected;

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
        result.current.sendMessage(testMessage);
    });

    await expect(server).toReceiveMessage(JSON.stringify(testMessage));
  });
});
