import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketMessage } from '@/types/chat';

export const WebSocketTest: React.FC = () => {
  const { status, messages, sendMessage } = useWebSocket();

  const handleSendMessage = () => {
    const message: WebSocketMessage = {
      type: 'message',
      payload: { text: 'Hello, from the client!' },
    };
    sendMessage(message);
  };

  return (
    <div>
      <h2>WebSocket Test</h2>
      <p>Connection Status: {status}</p>
      <button onClick={handleSendMessage} disabled={status !== 'OPEN'}>
        Send Message
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
