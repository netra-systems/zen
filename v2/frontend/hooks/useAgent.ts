
import { useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { UserMessage, StopAgent } from '../types';

export const useAgent = () => {
  const webSocket = useWebSocket();

  const sendUserMessage = useCallback((text: string) => {
    const message: UserMessage = {
      text,
    };
    webSocket?.sendMessage('user_message', message);
  }, [webSocket]);

  const stopAgent = useCallback(() => {
    const message: StopAgent = {
      run_id: '' // The backend will know which run to stop
    };
    webSocket?.sendMessage('stop_agent', message);
  }, [webSocket]);

  return { sendUserMessage, stopAgent };
};
