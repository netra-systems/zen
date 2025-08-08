
"use client";

import React, { useState } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';

const MessageInput: React.FC = () => {
  const [text, setText] = useState('');
  const { sendMessage } = useWebSocket();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      sendMessage(text);
      setText('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-gray-200">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full p-2 border rounded"
        placeholder="Type a message..."
      />
    </form>
  );
};

export default MessageInput;
