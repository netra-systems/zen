
import React from 'react';
import { Message, MessageOrchestratorProps } from '@/types/index';
import { UserMessageCard } from './UserMessageCard';
import { AgentMessageCard } from './AgentMessageCard';

export const MessageOrchestrator: React.FC<MessageOrchestratorProps> = ({ message }) => {
  switch (message.type) {
    case 'user':
      return <UserMessageCard message={message} />;
    case 'agent':
      return <AgentMessageCard message={message} />;
    default:
      // Per instruction 1:0:6, not all events are shown to the user by default.
      // Returning null for other message types for now.
      return null;
  }
};
