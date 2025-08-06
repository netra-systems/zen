import { renderHook, act } from '@testing-library/react-hooks';
import { useWebSocket } from '../app/hooks/useWebSocket';
import { w3cwebsocket as W3CWebSocket } from 'websocket';

global.WebSocket = W3CWebSocket as any;

describe('useWebSocket', () => {
  it('should connect to the WebSocket server and perform a handshake', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await waitForNextUpdate();

    expect(result.current.isConnected).toBe(true);
  });
});
