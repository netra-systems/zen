
"use client";

import React from 'react';
import Header from './Header';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

const ChatPage: React.FC = () => {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <MessageList />
      <MessageInput />
      <StopButton />
    </div>
  );
};

export default ChatPage;
