import { renderHook, act } from '@testing-library/react-hooks';
import { useWebSocket } from '../app/hooks/useWebSocket';
import { w3cwebsocket as W3CWebSocket } from 'websocket';

global.WebSocket = W3CWebSocket as any;

describe('useWebSocket', () => {
  it('should connect to the WebSocket server, perform a handshake, and handle JSON messages', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useWebSocket('ws://localhost:8000/ws/123'));

    await waitForNextUpdate();

    expect(result.current.isConnected).toBe(true);

    const testMessage = { type: 'test', payload: 'hello' };

    act(() => {
      // Simulate receiving a message from the server
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(testMessage),
      });
      (global.WebSocket as any).dispatchEvent(messageEvent);
    });

    expect(result.current.messages).toEqual([testMessage]);

    act(() => {
      result.current.sendMessage(testMessage);
    });

    // This part of the test would require a mock server to verify the message was sent.
    // For now, we just ensure the function doesn't crash.
  });
});