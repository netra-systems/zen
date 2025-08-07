'use client';

import { MessageCard } from './MessageCard';
import { Message } from '../types';

interface ChatHistoryProps {
  messages: Message[];
}

export function ChatHistory({ messages }: ChatHistoryProps) {
  return (
    <div className="w-full max-w-2xl flex-grow overflow-y-auto">
      {messages.map((msg, index) => (
        <MessageCard key={index} message={msg} />
      ))}
    </div>
  );
}