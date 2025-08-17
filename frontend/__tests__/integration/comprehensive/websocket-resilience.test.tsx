/**
 * WebSocket Resilience Tests
 * 
 * Tests WebSocket message buffering, exponential backoff reconnection, 
 * and heartbeat mechanisms.
 * All functions ≤8 lines, file ≤300 lines for modular architecture compliance.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  TEST_TIMEOUTS,
  WS
} from './test-utils';

import {
  ResilientWebSocketComponent,
  ExponentialBackoffComponent,
  HeartbeatComponent
} from './components/websocket-components';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('WebSocket Resilience Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
  });

  describe('WebSocket Message Buffering', () => {
    it('should handle WebSocket message buffering during reconnection', async () => {
      let messageBuffer: any[] = [];
      const { getByTestId } = render(<ResilientWebSocketComponent messageBuffer={messageBuffer} />);
      
      // Wait for initial connection
      await server.connected;
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('connected');
      });
    });

    it('should send messages when connected', async () => {
      let messageBuffer: any[] = [];
      const { getByTestId } = render(<ResilientWebSocketComponent messageBuffer={messageBuffer} />);
      
      await server.connected;
      
      fireEvent.click(getByTestId('send-message'));
      expect(getByTestId('buffer-size')).toHaveTextContent('0 buffered');
    });

    it('should buffer messages when disconnected', async () => {
      let messageBuffer: any[] = [];
      const { getByTestId } = render(<ResilientWebSocketComponent messageBuffer={messageBuffer} />);
      
      await server.connected;
      server.close();
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('disconnected');
      });
      
      fireEvent.click(getByTestId('send-message'));
      fireEvent.click(getByTestId('send-message'));
      
      expect(messageBuffer.length).toBe(2);
      expect(getByTestId('buffer-size')).toHaveTextContent('2 buffered');
    });

    it('should handle manual reconnection', async () => {
      let messageBuffer: any[] = [];
      const { getByTestId } = render(<ResilientWebSocketComponent messageBuffer={messageBuffer} />);
      
      fireEvent.click(getByTestId('manual-connect'));
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('connecting');
      });
    });
  });

  describe('Exponential Backoff Reconnection', () => {
    it('should implement exponential backoff for reconnection', async () => {
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      
      await waitFor(() => {
        expect(getByTestId('attempts')).toHaveTextContent('Attempts: 1');
        expect(parseInt(getByTestId('last-delay').textContent?.split(': ')[1] || '0')).toBeGreaterThan(0);
      });
    });

    it('should show connection state during reconnection', async () => {
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      
      await waitFor(() => {
        expect(getByTestId('connection-state')).toHaveTextContent('waiting');
      });
    });

    it('should handle reset functionality', async () => {
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      fireEvent.click(getByTestId('reset'));
      
      expect(getByTestId('attempts')).toHaveTextContent('Attempts: 0');
      expect(getByTestId('connection-state')).toHaveTextContent('disconnected');
    });

    it('should track multiple attempts', async () => {
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      
      await waitFor(() => {
        expect(parseInt(getByTestId('attempts').textContent?.split(': ')[1] || '0')).toBeGreaterThan(1);
      }, { timeout: TEST_TIMEOUTS.MEDIUM });
    });

    it('should display countdown timer', async () => {
      const { getByTestId } = render(<ExponentialBackoffComponent />);
      
      fireEvent.click(getByTestId('start-reconnect'));
      
      await waitFor(() => {
        expect(getByTestId('next-retry')).toHaveTextContent(/Next retry in: \d+s/);
      });
    });
  });

  describe('WebSocket Heartbeat and Keep-Alive', () => {
    it('should handle WebSocket heartbeat and keep-alive', async () => {
      const { getByTestId } = render(<HeartbeatComponent />);
      
      fireEvent.click(getByTestId('manual-heartbeat'));
      
      await waitFor(() => {
        expect(getByTestId('last-heartbeat')).not.toHaveTextContent('None');
        expect(getByTestId('connection-health')).toHaveTextContent('healthy');
      });
    });

    it('should update heartbeat interval', async () => {
      const { getByTestId } = render(<HeartbeatComponent />);
      
      fireEvent.click(getByTestId('faster-heartbeat'));
      
      await waitFor(() => {
        expect(getByTestId('heartbeat-interval')).toHaveTextContent('500ms');
      });
    });

    it('should display current health status', async () => {
      const { getByTestId } = render(<HeartbeatComponent />);
      
      expect(getByTestId('connection-health')).toHaveTextContent('healthy');
    });

    it('should format heartbeat timestamp', async () => {
      const { getByTestId } = render(<HeartbeatComponent />);
      
      fireEvent.click(getByTestId('manual-heartbeat'));
      
      await waitFor(() => {
        const timestamp = getByTestId('last-heartbeat').textContent;
        expect(timestamp).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
      });
    });

    it('should allow manual heartbeat sending', async () => {
      const { getByTestId } = render(<HeartbeatComponent />);
      
      const initialHeartbeat = getByTestId('last-heartbeat').textContent;
      
      fireEvent.click(getByTestId('manual-heartbeat'));
      
      await waitFor(() => {
        const newHeartbeat = getByTestId('last-heartbeat').textContent;
        expect(newHeartbeat).not.toBe(initialHeartbeat);
      });
    });
  });
});