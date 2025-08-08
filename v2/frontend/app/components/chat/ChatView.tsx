
import React from 'react';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { useChatStore } from '../store/chat';

const ChatView = () => {
  const messages = useChatStore((state) => state.messages);

  return (
    <div className="flex flex-col h-full">
      <ChatHeader subAgentName="Log Analyzer" subAgentStatus="Online" />
      <MessageList messages={messages} />
      <ChatInput />
    </div>
  );
};

export default ChatView;
