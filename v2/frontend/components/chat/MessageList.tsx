import React, { useEffect, useRef } from 'react';
import { useChatStore } from '@/store';
import { MessageItem } from './MessageItem';
import { ScrollArea } from '@/components/ui/scroll-area';

export const MessageList: React.FC = () => {
  const { messages } = useChatStore();
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <ScrollArea ref={scrollAreaRef} className="h-[calc(100vh-200px)] p-4">
      {messages
        .filter((msg) => msg.displayed_to_user)
        .map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}
    </ScrollArea>
  );
};
