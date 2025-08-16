
import { useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { UserMessage, StopAgent } from '../types';

export const useAgent = () => {
  const webSocket = useWebSocket();

  const sendUserMessage = useCallback((text: string) => {
    const message = {
      type: 'user_message' as const,
      payload: {
        content: text,
      },
    };
    webSocket?.sendMessage(message);
  }, [webSocket]);

  const stopAgent = useCallback(() => {
    const message = {
      type: 'stop_agent' as const,
      payload: {
        agent_id: '' // The backend will know which agent to stop
      },
    };
    webSocket?.sendMessage(message);
  }, [webSocket]);

  return { sendUserMessage, stopAgent };
};
