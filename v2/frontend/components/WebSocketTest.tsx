import React from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { WebSocketMessage } from '@/types/chat';

export const WebSocketTest: React.FC = () => {
  const { isConnected, lastMessage, sendMessage } = useWebSocket();

  const handleSendMessage = () => {
    const message: WebSocketMessage = {
      type: 'user_message',
      payload: { text: 'Hello, from the client!' },
    };
    sendMessage(message);
  };

  return (
    <div>
      <h2>WebSocket Test</h2>
      <p>Connection Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
      <button onClick={handleSendMessage} disabled={!isConnected}>
        Send Message
      </button>
      {lastMessage && (
        <div>
          <h3>Last Message Received:</h3>
          <pre>{JSON.stringify(lastMessage, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
