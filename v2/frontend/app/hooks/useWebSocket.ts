
import { useEffect, useRef, useState, useCallback } from 'react';

export enum WebSocketStatus {
  Connecting = 'Connecting',
  Open = 'Open',
  Closing = 'Closing',
  Closed = 'Closed',
  Error = 'Error',
}

export interface WebSocketHook {
  sendMessage: (message: object) => void;
  lastMessage: MessageEvent | null;
  status: WebSocketStatus;
  connect: (url: string) => void;
  disconnect: () => void;
}

export const useWebSocket = (): WebSocketHook => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
  const ws = useRef<WebSocket | null>(null);

  const connect = useCallback((url: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus(WebSocketStatus.Connecting);
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setStatus(WebSocketStatus.Open);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setStatus(WebSocketStatus.Closed);
      ws.current = null;
    };

    ws.current.onerror = (event) => {
      console.error('WebSocket error:', event);
      setStatus(WebSocketStatus.Error);
    };

    ws.current.onmessage = (message) => {
      setLastMessage(message);
    };
  }, []);

  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
  }, []);

  const sendMessage = useCallback((message: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { sendMessage, lastMessage, status, connect, disconnect };
};
