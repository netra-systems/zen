'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { WebSocketError } from '@/types/backend_schema_auto_generated';

export interface WebSocketOptions {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: WebSocketError) => void;
  onMessage?: (data: any) => void;
  onReconnectAttempt?: (attemptNumber: number) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enableReconnect?: boolean;
}


export interface UseWebSocketReturn {
  readyState: number;
  connectionId: string | null;
  lastMessage: any;
  error: WebSocketError | null;
  reconnectStrategy: 'exponential' | 'linear' | 'none';
  sendMessage: (message: any) => void;
  connect: () => void;
  disconnect: () => void;
}

export const useWebSocket = (url: string, options?: WebSocketOptions): UseWebSocketReturn => {
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<WebSocketError | null>(null);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [reconnectStrategy, setReconnectStrategy] = useState<'exponential' | 'linear' | 'none'>('exponential');
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const messageQueue = useRef<any[]>([]);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      if (ws.current?.readyState === WebSocket.OPEN) {
        return;
      }

      const newConnectionId = uuidv4();
      setConnectionId(newConnectionId);
      
      ws.current = new WebSocket(url);
      
      ws.current.onopen = () => {
        setReadyState(WebSocket.OPEN);
        reconnectAttempt.current = 0;
        
        // Send queued messages
        while (messageQueue.current.length > 0) {
          const msg = messageQueue.current.shift();
          ws.current?.send(JSON.stringify(msg));
        }
        
        options?.onOpen?.();
      };
      
      ws.current.onclose = () => {
        setReadyState(WebSocket.CLOSED);
        options?.onClose?.();
        
        // Attempt reconnection
        if (options?.enableReconnect !== false && 
            reconnectAttempt.current < (options?.maxReconnectAttempts ?? 10)) {
          const delay = reconnectStrategy === 'exponential' 
            ? Math.min(1000 * Math.pow(2, reconnectAttempt.current), 30000)
            : options?.reconnectInterval ?? 1000;
            
          reconnectTimer.current = setTimeout(() => {
            reconnectAttempt.current++;
            options?.onReconnectAttempt?.(reconnectAttempt.current);
            connect();
          }, delay);
        }
      };
      
      ws.current.onerror = (event) => {
        const errorObj: WebSocketError = {
          error_type: 'CONNECTION_ERROR',
          message: 'WebSocket connection error'
        };
        setError(errorObj);
        options?.onError?.(errorObj);
      };
      
      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          
          // Handle error messages
          if (data.type === 'error') {
            const errorObj: WebSocketError = {
              error_type: data.type,
              code: data.code,
              message: data.message
            };
            setError(errorObj);
            options?.onError?.(errorObj);
            
            // Set reconnect strategy based on error type
            if (data.code === 'INTERNAL_SERVER_ERROR') {
              setReconnectStrategy('exponential');
            }
          }
          
          options?.onMessage?.(data);
        } catch (e) {
          const parseError: WebSocketError = {
            error_type: 'PARSE_ERROR',
            message: `Failed to parse JSON: ${e}`
          };
          setError(parseError);
          options?.onError?.(parseError);
        }
      };
    } catch (err) {
      const connectionError: WebSocketError = {
        error_type: 'CONNECTION_ERROR',
        message: `Failed to connect: ${err}`
      };
      setError(connectionError);
      options?.onError?.(connectionError);
    }
  }, [url, options, reconnectStrategy]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setReadyState(WebSocket.CLOSED);
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      // Queue message for later
      messageQueue.current.push(message);
    }
  }, []);

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    readyState,
    connectionId,
    lastMessage,
    error,
    reconnectStrategy,
    sendMessage,
    connect,
    disconnect
  };
};