import React, { useState, useContext } from 'react';
import { WebSocketContext } from '@/contexts/WebSocketContext';
import ChatHistory from '../ChatHistory';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const Chat: React.FC = () => {
  const ws = useContext(WebSocketContext);
  const [newMessage, setNewMessage] = useState('');

  const handleSendMessage = () => {
    if (ws && newMessage.trim()) {
      ws.sendMessage(newMessage);
      setNewMessage('');
    }
  };

  const handleStop = () => {
    if (ws) {
      ws.stopProcessing();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <ChatHistory />
      <div className="p-4 border-t">
        <div className="flex space-x-2">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type a message..."
          />
          <Button onClick={handleSendMessage}>Send</Button>
          <Button onClick={handleStop} variant="destructive">Stop</Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
