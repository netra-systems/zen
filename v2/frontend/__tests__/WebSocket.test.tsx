
import { render, waitFor } from '@testing-library/react';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { useAuth } from '@/contexts/AuthContext';
import WS from 'jest-websocket-mock';

// Mock the useAuth hook
jest.mock('@/contexts/AuthContext', () => ({
  ...jest.requireActual('@/contexts/AuthContext'),
  useAuth: jest.fn(),
}));

const mockUser = { id: '123', full_name: 'Test User', email: 'test@example.com' };

describe('WebSocketProvider', () => {
  let server: WS;

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws/123');
    (useAuth as jest.Mock).mockReturnValue({ user: mockUser });
  });

  afterEach(() => {
    WS.clean();
  });

  it(
    'should connect and disconnect',
    async () => {
      render(
        <AuthProvider>
          <WebSocketProvider url={`ws://localhost:8000/ws/${mockUser.id}`}>
            <div>WebSocket Component</div>
          </WebSocketProvider>
        </AuthProvider>
      );

      await server.connected;

      expect(server.server.clients().length).toBe(1);

      server.close();

      await waitFor(() => {
        expect(server.server.clients().length).toBe(0);
      });
    },
    10000
  );
});
