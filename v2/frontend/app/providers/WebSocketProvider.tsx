
'use client';

import React, a s React from 'react';
import webSocketService from '@/app/services/websocket';

export const WebSocketContext = React.createContext(webSocketService);

export const WebSocketProvider: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  React.useEffect(() => {
    // This is where you would get the WebSocket URL from your config
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/ws';
    webSocketService.connect(wsUrl);
  }, []);

  return (
    <WebSocketContext.Provider value={webSocketService}>
      {children}
    </WebSocketContext.Provider>
  );
};
