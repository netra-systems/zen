import React from 'react';
import { Message } from '../types/chat';
import UserMessage from './UserMessage';
import AgentMessage from './AgentMessage';
import SystemMessage from './SystemMessage';

interface MessageListProps {
  messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((message, index) => {
        switch (message.type) {
          case 'user':
            return <UserMessage key={index} message={message.text} />;
          case 'agent':
            return <AgentMessage key={index} message={message.text} />;
          case 'system':
            return <SystemMessage key={index} message={message.text} />;
          default:
            return null;
        }
      })}
    </div>
  );
};

export default MessageList;