import { useState, useEffect, useCallback } from 'react';
import { getWebSocketClient } from '@/app/services/websocket';
import { useAuth } from '@/hooks/useAuth';

export const useWebSocket = () => {
  const { token } = useAuth();
  const [client, setClient] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    if (token) {
      const wsClient = getWebSocketClient(token);
      setClient(wsClient);

      wsClient.onmessage = (message) => {
        try {
          const data = JSON.parse(message.data as string);
          setMessages((prevMessages) => [...prevMessages, data]);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    }
  }, [token]);

  const sendMessage = useCallback(
    (message: any) => {
      if (client && client.readyState === client.OPEN) {
        client.send(JSON.stringify(message));
      } else {
        console.error('WebSocket is not connected.');
      }
    },
    [client]
  );

  return { messages, sendMessage };
};
