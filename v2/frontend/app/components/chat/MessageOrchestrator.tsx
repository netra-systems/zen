import React from 'react';
import { Message, MessageOrchestratorProps } from '@/app/types/index';

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  return <ChatMessage message={message} />;
};