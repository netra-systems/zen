import React, { useContext } from 'react';
import { WebSocketContext } from '@/contexts/WebSocketContext';
import Message from '../Message';

const ChatHistory: React.FC = () => {
  const ws = useContext(WebSocketContext);

  if (!ws) {
    return <div>Loading...</div>;
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {ws.messages.map((msg, index) => (
        <Message key={index} message={msg} />
      ))}
    </div>
  );
};

export default ChatHistory;
