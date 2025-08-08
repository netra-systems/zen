import React from 'react';
import { Header } from './Header';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { StopButton } from './StopButton';

const ChatLayout: React.FC = () => {
  return (
    <div className="flex flex-col h-screen">
      <Header />
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