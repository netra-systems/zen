import React, { useEffect, useRef } from 'react';
import { useChatStore } from '@/store/chat';
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
    <ScrollArea ref={scrollAreaRef} className="h-[calc(100vh-350px)] p-4">
      {messages.length === 0 && (
        <div className="flex justify-center items-center h-full">
          <div className="text-center">
            <h2 className="text-2xl font-semibold text-gray-500">Welcome to Netra Chat</h2>
            <p className="text-gray-400">Start a conversation by typing a message or selecting an example prompt.</p>
          </div>
        </div>
      )}
      {messages
        .filter((msg) => msg.displayed_to_user)
        .map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}
    </ScrollArea>
  );
};