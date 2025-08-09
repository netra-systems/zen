'use client';

import { useContext } from 'react';
import { useWebSocketContext } from '../providers/WebSocketProvider';

export const useWebSocket = () => {
  const context = useWebSocketContext();
  return context;
};
