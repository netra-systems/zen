
import { useAgentStreaming } from './useAgentStreaming';
import { getToken, getUserId } from '../lib/user';
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
          // Handle different event types from the backend
          switch (message.event) {
            case 'on_chain_start':
            case 'on_prompt_start':
            case 'on_chat_model_start':
              // We can handle these events to show some status
              break;
            case 'on_chat_model_stream':
              if (message.data && message.data.messages) {
                message.data.messages.forEach((msg: any) => {
                  addMessage(msg.content, 'agent', message.event);
                });
              }
              break;
            case 'on_chat_model_end':
            case 'on_chain_end':
              if (message.data && message.data.output && message.data.output.messages) {
                message.data.output.messages.forEach((msg: any) => {
                  addMessage(msg.content, 'agent', message.event, message.data);
                });
              }
              break;
            default:
              console.log('Received unhandled message:', message);
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
  }, [addMessage]);

  const startAgent = async (message: string) => {
    addMessage(message, 'user');
    if (socket && isConnected) {
      setShowThinking(true);
      try {
        const userId = getUserId();
        if (!userId) {
          console.error('User ID not found');
          return;
        }
        const analysisRequest = {
          settings: {
            debug_mode: false,
          },
          request: {
            id: runIdRef.current,
            user_id: userId,
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
