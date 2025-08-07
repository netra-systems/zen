
import React from 'react';
import { MessageOrchestratorProps } from '@/app/types/index';
import { ChatMessage } from './ChatMessage';

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ messages }) => {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((message, index) => (
        <ChatMessage key={index} message={message} />
      ))}
    </div>
  );
};
