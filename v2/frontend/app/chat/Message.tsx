
"use client";

import React from 'react';
import { WebSocketMessage } from '../../types';
import JsonViewer from './JsonViewer';

interface MessageProps {
  message: WebSocketMessage;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const renderPayload = () => {
    switch (message.type) {
      case 'user_message':
        return <div>{message.payload.text}</div>;
      case 'agent_message':
        return <div>{message.payload.text}</div>;
      case 'error':
        return <div className="text-red-500">{message.payload.message}</div>;
      case 'tool_started':
        return <div>Tool started: {message.payload.tool_name}</div>;
      case 'tool_completed':
        return (
          <div>
            <div>Tool completed: {message.payload.tool_name}</div>
            <JsonViewer data={message.payload.result} />
          </div>
        );
      default:
        return <JsonViewer data={message.payload} />;
    }
  };

  return (
    <div className="mb-4">
      <div className="font-bold">{message.type}</div>
      {renderPayload()}
    </div>
  );
};

export default Message;
