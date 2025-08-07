import { useEffect, useRef, useState, useCallback } from 'react';

export enum WebSocketStatus {
  Connecting,
  Open,
  Closing,
  Closed,
}

export interface WebSocketHook {
  sendMessage: (message: object) => void;
  lastMessage: MessageEvent | null;
  status: WebSocketStatus;
}

export const useWebSocket = (url: string | null): WebSocketHook => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
  const ws = useRef<WebSocket | null>(null);

  const sendMessage = useCallback((message: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    if (url) {
      setStatus(WebSocketStatus.Connecting);
      ws.current = new WebSocket(url);

      ws.current.onopen = () => setStatus(WebSocketStatus.Open);
      ws.current.onclose = () => setStatus(WebSocketStatus.Closed);
      ws.current.onmessage = (message) => setLastMessage(message);

      return () => {
        if (ws.current) {
          ws.current.close();
        }
      };
    }
  }, [url]);

  return { sendMessage, lastMessage, status };
};