import React from 'react';
import { Message, MessageOrchestratorProps } from '@/app/types';

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  return <ChatMessage message={message} />;
};