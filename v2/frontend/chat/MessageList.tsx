import React from 'react';
import { useChatStore } from '@/store';
import { Message } from './Message';
import { ScrollArea } from '@/components/ui/scroll-area';

export const MessageList: React.FC = () => {
  const { messages } = useChatStore();

  return (
    <ScrollArea className="h-[calc(100vh-200px)] p-4">
      {messages
        .filter((msg) => msg.displayed_to_user)
        .map((msg) => (
          <Message key={msg.id} message={msg} />
        ))}
    </ScrollArea>
  );
};
