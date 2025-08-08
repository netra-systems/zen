import React, { useState } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  onStopAgent: () => void;
}

const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, onStopAgent }) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <div className="p-4 border-t flex items-center">
      <input
        type="text"
        className="flex-1 border rounded-lg p-2"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
      />
      <button onClick={handleSend} className="ml-4 bg-blue-500 text-white p-2 rounded-lg">
        Send
      </button>
      <button onClick={onStopAgent} className="ml-4 bg-red-500 text-white p-2 rounded-lg">
        Stop
      </button>
    </div>
  );
};

export default MessageInput;
