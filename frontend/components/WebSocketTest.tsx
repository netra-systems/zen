import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { WebSocketMessage } from '@/types/unified';

export const WebSocketTest: React.FC = () => {
  const { status, messages, sendMessage } = useWebSocket();

  const handleSendMessage = () => {
    const message: WebSocketMessage = {
      type: 'message',
      payload: { content: 'Hello, from the client!' },
    };
    sendMessage(message);
  };

  return (
    <div data-testid="websocket-component">
      <h2>WebSocket Test</h2>
      <p data-testid="connection-status">Connection Status: {status}</p>
      <button onClick={handleSendMessage} disabled={status !== 'OPEN'} data-testid="connect-btn">
        Send Message
      </button>
      <button data-testid="disconnect-btn" disabled={status !== 'OPEN'}>
        Disconnect
      </button>
      <button data-testid="send-message-btn" onClick={handleSendMessage} disabled={status !== 'OPEN'}>
        Send Test Message
      </button>
      {messages.length > 0 && (
        <div>
          <h3>Last Message Received:</h3>
          <pre>{JSON.stringify(messages[messages.length - 1], null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
