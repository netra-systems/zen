'use client';

import React from 'react';
import { Message } from '@/app/types/chat';
import { ChatMessage } from './ChatMessage';
import { ArtifactCard } from './ArtifactCard';

interface MessageOrchestratorProps {
  message: Message;
}

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  if (message.artifact) {
    return <ArtifactCard artifact={message.artifact} />;
  }

  return <ChatMessage message={message} />;
};