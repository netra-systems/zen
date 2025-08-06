import { renderHook, act } from '@testing-library/react-hooks';
import { useAgent } from '../app/hooks/useAgent';
import { Server } from 'ws';

const mockServer = new Server({ port: 8080 });

describe('useAgent with WebSocket', () => {
  let server: Server;

  beforeAll(() => {
    server = new Server({ port: 8000 });
  });

  afterAll(() => {
    server.close();
  });

  it('should connect to WebSocket and perform handshake', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useAgent());

    await act(async () => {
      await waitForNextUpdate();
    });

    expect(result.current.isConnected).toBe(true);
  });

  it('should send a message and receive a response via WebSocket', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useAgent());
    const message = 'Test message';

    await act(async () => {
      await waitForNextUpdate();
    });

    act(() => {
      result.current.startAgent(message);
    });

    // Assert that the user message is added immediately
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe(message);
    expect(result.current.messages[0].sender).toBe('user');

    // Mock the server response
    server.on('connection', (ws) => {
      ws.on('message', (message) => {
        const data = JSON.parse(message.toString());
        if (data.input === 'Test message') {
          ws.send(JSON.stringify({ message: 'Test response' }));
        }
      });
    });

    await act(async () => {
      await waitForNextUpdate();
    });

    // Assert that the agent response is received
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].content).toBe('Test response');
    expect(result.current.messages[1].sender).toBe('agent');
  });
});