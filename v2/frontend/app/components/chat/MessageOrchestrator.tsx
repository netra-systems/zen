import React from 'react';
import { Message } from '@/app/types';
import { ChatMessage } from './ChatMessage';

interface MessageOrchestratorProps {
  message: Message;
}

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  return <ChatMessage message={message} />;
};