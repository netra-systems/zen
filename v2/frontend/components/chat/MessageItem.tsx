import React, { useState } from 'react';
import { WebSocketMessage } from '@/types';
import { RawJsonView } from './RawJsonView';

interface MessageItemProps {
  message: WebSocketMessage;
}

export const MessageItem = ({ message }: MessageItemProps) => {
  const [isRawViewOpen, setIsRawViewOpen] = useState(false);
  const { type, payload } = message;

  const renderPayload = () => {
    if (!payload) {
      return null;
    }

    switch (type) {
      case 'user_message':
        return <span>{payload.text}</span>;
      case 'agent_message':
        return <span>{payload.text}</span>;
      case 'tool_started':
        return <span>Tool started: {payload.tool_name}</span>;
      case 'tool_completed':
        return <span>Tool completed: {payload.tool_name}</span>;
      default:
        return <span>{JSON.stringify(payload)}</span>;
    }
  };

  return (
    <div className="p-2 my-2 bg-gray-100 rounded">
      <div className="flex justify-between">
        <div>
          <strong>{type}:</strong> {renderPayload()}
        </div>
        <button onClick={() => setIsRawViewOpen(!isRawViewOpen)} className="text-xs text-gray-500">
          {isRawViewOpen ? 'Hide Raw' : 'Show Raw'}
        </button>
      </div>
      {isRawViewOpen && <RawJsonView json={payload} />}
    </div>
  );
};
