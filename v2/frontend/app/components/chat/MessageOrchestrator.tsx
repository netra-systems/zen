import React from 'react';
import { MessageOrchestratorProps } from '@/app/types/index';
import { ChatMessage } from './ChatMessage';

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  return <ChatMessage message={message} />;
};