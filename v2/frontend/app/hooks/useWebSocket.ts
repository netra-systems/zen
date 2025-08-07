import { useEffect, useRef, useState } from 'react';

export const useWebSocket = (url: string) => {
  const [messages, setMessages] = useState<object[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const webSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    webSocketRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      ws.send('handshake');
    };

    ws.onmessage = (event) => {
      const message = event.data;
      if (message === 'handshake_ack') {
        setIsConnected(true);
        console.log('WebSocket handshake successful');
      } else {
        try {
          const parsedMessage = JSON.parse(message);
          setMessages((prevMessages) => [...prevMessages, parsedMessage]);
        } catch (error) {
          console.error('Error parsing WebSocket message JSON:', error);
          // Handle non-JSON messages if necessary
        }
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = (message: object) => {
    if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
      webSocketRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected.');
    }
  };

  return { messages, isConnected, sendMessage };
};
