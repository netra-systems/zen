
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '@/app/services/websocket';
import { WebSocketStatus } from '@/types';
import WS from 'jest-websocket-mock';

describe('useWebSocket', () => {
  let server: WS;
  const token = 'test-token';

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws?token=test-token');
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect to the server', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(token);
    });

    await server.connected;

    expect(result.current.status).toBe(WebSocketStatus.Open);
  });

  it('should send and receive messages', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(token);
    });

    await server.connected;

    const message = { type: 'test', payload: 'hello' };
    act(() => {
      result.current.sendMessage(message);
    });

    await expect(server).toReceiveMessage(JSON.stringify(message));

    const response = { type: 'response', payload: 'world' };
    act(() => {
      server.send(JSON.stringify(response));
    });

    expect(result.current.lastJsonMessage).toEqual(response);
  });

  it('should change status on disconnect', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(token);
    });

    await server.connected;

    expect(result.current.status).toBe(WebSocketStatus.Open);

    act(() => {
      result.current.disconnect();
    });

    await server.closed;

    expect(result.current.status).toBe(WebSocketStatus.Closed);
  });
});
