import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../app/hooks/useWebSocket';

describe('useWebSocket', () => {
  it('should connect, handshake, and handle JSON messages', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await waitFor(() => expect((global.WebSocket as any).lastInstance).not.toBeNull());
    const socket = (global.WebSocket as any).lastInstance;

    act(() => {
      socket.onmessage(new MessageEvent('message', { data: 'handshake_ack' }));
    });

    await waitFor(() => expect(result.current.isConnected).toBe(true));

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
        socket.onmessage(new MessageEvent('message', { data: JSON.stringify(testMessage) }));
    });

    await waitFor(() => expect(result.current.messages).toEqual([testMessage]));
  });
});
