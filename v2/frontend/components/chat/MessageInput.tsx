import React, { useState } from 'react';
import { useWebSocket } from '@/contexts/WebSocketContext';

export const MessageInput = () => {
  const [message, setMessage] = useState('');
  const { sendMessage } = useWebSocket();

  const handleSend = () => {
    if (message.trim()) {
      sendMessage({ type: 'user_message', payload: { text: message } });
      setMessage('');
    }
  };

  return (
    <div className="p-4">
      <input
        type="text"
        className="w-full p-2 border rounded"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
      />
      <button onClick={handleSend} className="mt-2 p-2 w-full bg-blue-500 text-white rounded">
        Send
      </button>
    </div>
  );
};
