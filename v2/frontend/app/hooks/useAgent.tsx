import { useAgentStreaming } from './useAgentStreaming';
import { getToken } from '../lib/user';
import { useEffect, useRef, useState } from 'react';

export function useAgent() {
  const { addMessage, processStream, setShowThinking, ...rest } = useAgentStreaming();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const runIdRef = useRef<string | null>(null);

  useEffect(() => {
    const connect = async () => {
      const token = await getToken();
      if (token) {
        const runId = `run_${Date.now()}`;
        runIdRef.current = runId;
        const ws = new WebSocket(`ws://localhost:8000/agent/${runId}?token=${token}`);
        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          ws.send(JSON.stringify({ type: 'handshake', message: 'Hello from client' }));
        };
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'handshake' && message.message === 'Hello from server') {
            console.log('Handshake successful');
          } else {
            processStream(event.data);
          }
        };
        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
        };
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
        setSocket(ws);
      }
    };

    connect();

    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);

  const startAgent = async (message: string) => {
    addMessage(message, 'user');
    if (socket && isConnected) {
      setShowThinking(true);
      try {
        const analysisRequest = {
          request: {
            id: runIdRef.current,
            query: message,
            workloads: [],
          },
        };
        socket.send(JSON.stringify({ action: 'start_agent', payload: analysisRequest }));
      } catch (error) {
        console.error('Error sending message:', error);
      } finally {
        setShowThinking(false);
      }
    }
  };

  return { startAgent, addMessage, setShowThinking, ...rest };
}
