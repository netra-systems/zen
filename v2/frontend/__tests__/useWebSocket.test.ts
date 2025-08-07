import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../app/hooks/useWebSocket';
import { WebSocket } from 'ws';

describe('useWebSocket', () => {
  it('should connect, handshake, and handle JSON messages', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    const socket = (WebSocket as any).lastInstance;

    act(() => {
      socket.emit('message', { data: 'handshake_ack' });
    });

    expect(result.current.isConnected).toBe(true);

    const testMessage = { type: 'test', payload: 'hello' };
    act(() => {
        socket.emit('message', { data: JSON.stringify(testMessage) });
    });

    expect(result.current.messages).toEqual([testMessage]);
  });
});