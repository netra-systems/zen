"use client";

import React from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { useChatStore } from '@/store/chat';

const MainChat: React.FC = () => {
  const { isProcessing } = useChatStore();

  return (
    <div className="flex h-screen bg-gray-100">
      <div className="flex flex-col flex-1">
        <ChatHeader />
        <div className="flex-grow overflow-y-auto">
          <ExamplePrompts />
          <MessageList />
        </div>
        <div className="p-4 bg-white border-t">
          <MessageInput />
          {isProcessing && <StopButton />}
        </div>
      </div>
    </div>
  );
};

export default MainChat;