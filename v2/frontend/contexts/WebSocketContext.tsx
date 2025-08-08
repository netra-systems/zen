import React, { createContext, ReactNode } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

interface WebSocketContextType {
  sendMessage: (message: string) => void;
  lastMessage: MessageEvent | null;
  readyState: ReadyState;
}

export const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode, url: string | null }> = ({ children, url }) => {
  if (!url) {
    return <>{children}</>;
  }
  const { sendMessage, lastMessage, readyState } = useWebSocket(url, { shouldReconnect: (closeEvent) => true });

  return (
    <WebSocketContext.Provider value={{ sendMessage, lastMessage, readyState }}>
      {children}
    </WebSocketContext.Provider>
  );
};