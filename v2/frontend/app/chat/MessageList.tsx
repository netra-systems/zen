
"use client";

import React from 'react';

import { useWebSocket } from '../contexts/WebSocketContext';
import Message from './Message';


const MessageList: React.FC = () => {
  const { messages } = useWebSocket();

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((msg, index) => (
        <Message key={index} message={msg as any} />
      ))}
    </div>
  );
};

export default MessageList;
