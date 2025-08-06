'use client';

import React, { useState, useEffect } from 'react';
import { ChatInput } from './ChatInput';
import { ChatHistory } from './ChatHistory';
import { useWebSocket } from '../hooks/useWebSocket';
import { Message } from '../types';

const WS_URL = 'ws://localhost:8000/ws/123';

export const Dashboard = () => {
  const { messages: wsMessages, isConnected, sendMessage } = useWebSocket(WS_URL);
  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    const newMessages = wsMessages.map((msg) => ({ role: 'assistant', content: msg }));
    setMessages((prevMessages) => [...prevMessages, ...newMessages]);
  }, [wsMessages]);

  const handleSendMessage = (message: string) => {
    const userMessage: Message = { role: 'user', content: message };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    sendMessage(message);
  };

  return (
    <div className="flex flex-col h-full items-center justify-center">
      <div className="w-full max-w-2xl flex flex-col h-full">
        <ChatHistory messages={messages} />
        <div className="mt-4">
          <ChatInput onSendMessage={handleSendMessage} />
        </div>
        <div className="flex justify-center space-x-4 mt-4">
          <p className="text-sm text-gray-500">
            WebSocket status: {isConnected ? 'Connected' : 'Disconnected'}
          </p>
        </div>
      </div>
    </div>
  );
};
