'use client';

import { ChatMessage } from './ChatMessage';
import { Message } from '../types';

interface ChatHistoryProps {
  messages: Message[];
}

export function ChatHistory({ messages }: ChatHistoryProps) {
  return (
    <div className="w-full max-w-2xl flex-grow overflow-y-auto">
      {messages.map((msg, index) => (
        <ChatMessage key={index} message={msg} />
      ))}
    </div>
  );
}