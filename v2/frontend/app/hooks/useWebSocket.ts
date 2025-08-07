import { useEffect, useRef, useState, useCallback } from 'react';

export const useWebSocket = (url: string) => {
  const [messages, setMessages] = useState<object[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const webSocketRef = useRef<WebSocket | null>(null);
  const reconnectInterval = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    webSocketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      if (reconnectInterval.current) {
        clearInterval(reconnectInterval.current);
        reconnectInterval.current = null;
      }
      ws.send('handshake');
    };

    ws.onmessage = (event) => {
      const message = event.data;
      if (message === 'handshake_ack') {
        console.log('WebSocket handshake successful');
      } else {
        try {
          const parsedMessage = JSON.parse(message);
          setMessages((prevMessages) => [...prevMessages, parsedMessage]);
        } catch (error) {
          console.error('Error parsing WebSocket message JSON:', error);
        }
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      if (!reconnectInterval.current) {
        reconnectInterval.current = setInterval(() => {
          console.log('Attempting to reconnect WebSocket...');
          connect();
        }, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (webSocketRef.current) {
        webSocketRef.current.close();
      }
      if (reconnectInterval.current) {
        clearInterval(reconnectInterval.current);
      }
    };
  }, [connect]);

  const sendMessage = (message: object) => {
    if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
      webSocketRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected.');
    }
  };

  return { messages, isConnected, sendMessage };
};
