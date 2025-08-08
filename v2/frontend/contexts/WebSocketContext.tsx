import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { webSocketService, WebSocketStatus } from '../services/webSocketService';
import { Message, MessageType } from '@/types';

interface WebSocketContextType {
  status: WebSocketStatus;
  sendMessage: (message: string) => void;
  stopProcessing: () => void;
  messages: Message[];
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<WebSocketStatus>('CLOSED');
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    webSocketService.onStatusChange = setStatus;
    webSocketService.onMessage = (message) => {
      if (message.type === 'message') {
        setMessages((prevMessages) => [...prevMessages, message.payload as Message]);
      }
    };
    webSocketService.connect();

    return () => {
      webSocketService.disconnect();
    };
  }, []);

  const sendMessage = (message: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      created_at: new Date(),
      content: message,
      type: MessageType.USER,
      displayed_to_user: true,
    };
    webSocketService.sendMessage({ type: 'user_message', payload: { text: message } });
    setMessages((prevMessages) => [...prevMessages, userMessage]);
  };

  const stopProcessing = () => {
    webSocketService.sendMessage({ type: 'stop_agent', payload: { run_id: 'TODO' } });
  };

  return (
    <WebSocketContext.Provider value={{ status, sendMessage, stopProcessing, messages }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};