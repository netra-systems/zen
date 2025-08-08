
import { useContext } from 'react';
import { WebSocketContext } from '@/app/providers/WebSocketProvider';

export const useWebSocket = () => {
  return useContext(WebSocketContext);
};
