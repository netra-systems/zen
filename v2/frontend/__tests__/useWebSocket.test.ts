import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket, WebSocketStatus } from '../app/hooks/useWebSocket';
import WS from 'jest-websocket-mock';

describe('useWebSocket', () => {
  let server: WS;
  const wsUrl = 'ws://localhost:8000/ws/123';

  beforeEach(() => {
    server = new WS(wsUrl, { jsonProtocol: true });
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect and change status to Open', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(wsUrl);
    });

    await server.connected;

    await waitFor(() => expect(result.current.status).toBe(WebSocketStatus.Open));
  });

  it('should receive messages', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(wsUrl);
    });

    await server.connected;

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
      server.send(testMessage);
    });

    await waitFor(() => expect(JSON.parse(result.current.lastMessage!.data)).toEqual(testMessage));
  });

  it('should send messages', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(wsUrl);
    });

    await server.connected;

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
      result.current.sendMessage(testMessage);
    });

    await expect(server).toReceiveMessage(testMessage);
  });

  it('should disconnect and change status to Closed', async () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      result.current.connect(wsUrl);
    });

    await server.connected;

    await waitFor(() => expect(result.current.status).toBe(WebSocketStatus.Open));

    act(() => {
      result.current.disconnect();
    });

    await waitFor(() => expect(result.current.status).toBe(WebSocketStatus.Closed));
  });
});