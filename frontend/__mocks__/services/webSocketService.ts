export type WebSocketStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED';
export type WebSocketState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

const createMockWebSocketService = () => {
  const service = {
    connect: jest.fn(),
    disconnect: jest.fn(),
    sendMessage: jest.fn(),
    send: jest.fn(),
    getState: jest.fn(() => 'disconnected' as WebSocketState),
    onStatusChange: null as ((status: WebSocketStatus) => void) | null,
    onMessage: null as ((message: any) => void) | null,
  };
  
  // Simulate async connection behavior
  service.connect.mockImplementation((url: string) => {
    // Immediately call status change handler to simulate connection
    if (service.onStatusChange) {
      service.onStatusChange('CONNECTING');
      // Simulate successful connection after short delay
      setTimeout(() => {
        if (service.onStatusChange) {
          service.onStatusChange('OPEN');
        }
      }, 50);
    }
  });
  
  return service;
};

export const webSocketService = createMockWebSocketService();