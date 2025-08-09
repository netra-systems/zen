
"use client";

import React from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';

const ChatPage: React.FC = () => {
  return (
    <div className="flex h-screen">
      <div className="flex flex-col flex-1">
        <ChatHeader />
        <ExamplePrompts />
        <MessageList />
        <MessageInput />
        <StopButton />
      </div>
    </div>
  );
};

export default ChatPage;
