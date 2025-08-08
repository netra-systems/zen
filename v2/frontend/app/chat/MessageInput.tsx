"use client";

import React, { useState } from 'react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { useAgent } from '../hooks/useAgent';

const MessageInput: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const { sendUserMessage } = useAgent();

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      sendUserMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="p-4 border-t flex">
      <Input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
        placeholder="Type your message..."
        className="flex-1"
      />
      <Button onClick={handleSendMessage} className="ml-2">
        Send
      </Button>
    </div>
  );
};

export default MessageInput;