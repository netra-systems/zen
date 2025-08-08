import webSocketService from '@/services/websocket';
import { WebSocketStatus } from '@/types';
import WS from 'jest-websocket-mock';

jest.mock('@/types', () => ({
  ...jest.requireActual('@/types'),
  __esModule: true,
  default: {
    api: {
      wsBaseUrl: 'ws://localhost:8000/ws',
    },
  },
}));

const token = 'test-token';
const server = new WS('ws://localhost:8000/ws/ws?token=test-token');

describe('WebSocketService', () => {
  afterEach(() => {
    WS.clean();
  });

  it('should connect to the server', async () => {
    let status: WebSocketStatus | null = null;
    webSocketService.onStatusChange((newStatus) => {
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
    webSocketService.onMessage((message) => {
      receivedMessage = message;
    });

    const message = { type: 'test', payload: 'hello' };
    webSocketService.sendMessage(message);

    await expect(server).toReceiveMessage(JSON.stringify(message));

    const response = { type: 'response', payload: 'world' };
    server.send(JSON.stringify(response));

    expect(receivedMessage).toEqual(response);
  });

  it('should change status on disconnect', async () => {
    let status: WebSocketStatus | null = null;
    webSocketService.onStatusChange((newStatus) => {
      status = newStatus;
    });

    webSocketService.connect(token);
    await server.connected;

    webSocketService.disconnect();
    await server.closed;

    expect(status).toBe(WebSocketStatus.Closed);
  });
});