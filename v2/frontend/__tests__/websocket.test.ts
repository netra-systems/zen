import { WebSocketStatus } from '@/types';
import WS from 'jest-websocket-mock';

describe('WebSocketService', () => {
  let server: WS;
  let webSocketService: any; // instance of WebSocketService
  const token = 'test-token';

  beforeEach(() => {
    jest.resetModules(); // This is the key
    webSocketService = require('@/services/websocketService').default;
    server = new WS('ws://localhost:8000/ws?token=test-token');
  });

  afterEach(() => {
    WS.clean();
  });

  it('should connect to the server', async () => {
    let status: WebSocketStatus | null = null;
    webSocketService.onStatusChange((newStatus: WebSocketStatus) => {
      status = newStatus;
    });
    webSocketService.connect(token);
    await server.connected;
    expect(status).toBe(WebSocketStatus.Open);
  });

  it('should send and receive messages', async () => {
    webSocketService.connect(token);
    await server.connected;

    let receivedMessage: any = null;
    webSocketService.onMessage((message: any) => {
      receivedMessage = message;
    });

    const message = { type: 'test', payload: 'hello' };
    // The webSocketService is now connected, so readyState should be OPEN
    webSocketService.sendMessage(message);

    await expect(server).toReceiveMessage(JSON.stringify(message));

    const response = { type: 'response', payload: 'world' };
    server.send(JSON.stringify(response));

    // Wait for the message to be processed
    await new Promise(resolve => process.nextTick(resolve));

    expect(receivedMessage).toEqual(response);
  });

  it('should change status on disconnect', async () => {
    let status: WebSocketStatus | null = null;
    webSocketService.onStatusChange((newStatus: WebSocketStatus) => {
      status = newStatus;
    });

    webSocketService.connect(token);
    await server.connected;
    // At this point, status should be Open
    expect(status).toBe(WebSocketStatus.Open);

    webSocketService.disconnect();
    await server.closed;

    expect(status).toBe(WebSocketStatus.Closed);
  });
});