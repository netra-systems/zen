
import { useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { UserMessage, StopAgent } from '../types';

export const useAgent = () => {
  const webSocket = useWebSocket();

  const sendUserMessage = useCallback((text: string) => {
    const message = {
      type: 'message' as const,
      payload: {
        content: text,
      },
    };
    webSocket?.sendMessage(message);
  }, [webSocket]);

  const stopAgent = useCallback(() => {
    const message = {
      type: 'message' as const,
      payload: {
        run_id: '' // The backend will know which run to stop
      },
    };
    webSocket?.sendMessage(message);
  }, [webSocket]);

  return { sendUserMessage, stopAgent };
};
