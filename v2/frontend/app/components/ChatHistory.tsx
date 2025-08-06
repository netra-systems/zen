
'use client';

import useAppStore from '@/store';
import { ChatMessage } from './ChatMessage';

export function ChatHistory() {
  const messages = useAppStore((state) => state.messages);

  return (
    <div className="w-full max-w-2xl flex-grow overflow-y-auto">
      {messages.map((msg, index) => (
        <ChatMessage key={index} message={msg} />
      ))}
    </div>
  );
}
