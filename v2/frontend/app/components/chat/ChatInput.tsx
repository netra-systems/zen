import React, { useState } from 'react';
import { useChatStore } from '../store/chat';

const ChatInput = () => {
  const [inputValue, setInputValue] = useState('');
  const addMessage = useChatStore((state) => state.addMessage);

  const handleSend = () => {
    if (inputValue.trim()) {
      addMessage({ type: 'user', text: inputValue });
      setInputValue('');
    }
  };

  return (
    <div className="p-4">
      <div className="flex items-center">
        <input
          type="text"
          className="flex-1 p-2 border rounded-l-md"
          placeholder="Type your message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        />
        <button
          className="px-4 py-2 bg-blue-500 text-white rounded-r-md"
          onClick={handleSend}
        >
          Send
        </button>
        <button className="ml-2 px-4 py-2 bg-red-500 text-white rounded-md">
          Stop
        </button>
      </div>
    </div>
  );
};

export default ChatInput;