import React from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';

const ChatLayout: React.FC = () => {
  return (
    <div className="flex flex-col h-screen">
      <ChatHeader />
      <div className="flex-grow">
        <MessageList />
      </div>
      <div className="p-4">
        <StopButton />
      </div>
      <MessageInput />
    </div>
  );
};

export default ChatLayout;