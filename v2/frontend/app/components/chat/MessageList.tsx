import React from 'react';
import {
  WebSocketMessage,
  UserMessage as UserMessageProps,
  AgentMessage as AgentMessageProps,
  WebSocketError,
  ToolStarted,
  ToolCompleted,
} from '@/app/types';
import UserMessage from './messages/UserMessage';
import AgentMessage from './messages/AgentMessage';
import ErrorMessage from './messages/ErrorMessage';
import ToolMessage from './messages/ToolMessage';

interface MessageListProps {
  messages: WebSocketMessage[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((msg, index) => {
        switch (msg.type) {
          case 'user_message':
            return <UserMessage key={index} {...(msg.payload as UserMessageProps)} />;
          case 'agent_message':
            return <AgentMessage key={index} {...(msg.payload as AgentMessageProps)} />;
          case 'error':
            return <ErrorMessage key={index} {...(msg.payload as WebSocketError)} />;
          case 'tool_started':
          case 'tool_completed':
            return <ToolMessage key={index} message={msg.payload as ToolStarted | ToolCompleted} />;
          default:
            return (
              <div key={index} className="p-2">
                <pre>{JSON.stringify(msg, null, 2)}</pre>
              </div>
            );
        }
      })}
    </div>
  );
};

export default MessageList;