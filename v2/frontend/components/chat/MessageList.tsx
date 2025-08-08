import React from 'react';
import { useChat } from '@/contexts/ChatContext';
import { MessageItem } from './MessageItem';

export const MessageList = () => {
  const { state } = useChat();

  return (
    <div className="flex-1 p-4 overflow-y-auto">
      {state.messages.map((msg, index) => (
        <MessageItem key={index} message={msg} />
      ))}
    </div>
  );
};