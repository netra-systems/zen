
"use client";

import React from 'react';
import Header from './Header';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import StopButton from './StopButton';
import Sidebar from './Sidebar';

const ChatPage: React.FC = () => {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-col flex-1">
        <Header />
        <MessageList />
        <MessageInput />
        <StopButton />
      </div>
    </div>
  );
};

export default ChatPage;
