"use client";

import React from 'react';
import { useChatStore } from '../store';
import Message from './Message';

const MessageList: React.FC = () => {
  const { messages } = useChatStore();

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((msg, index) => (
        <Message key={index} message={msg} />
      ))}
    </div>
  );
};

export default MessageList;