import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store';

export const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const { sendMessage } = useWebSocket();
  const { setProcessing, isProcessing } = useChatStore();

  const handleSend = () => {
    if (message.trim()) {
      sendMessage(JSON.stringify({ type: 'user_message', payload: { text: message } }));
      setProcessing(true);
      setMessage('');
    }
  };

  return (
    <div className="p-4 border-t flex">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder={isProcessing ? "Agent is thinking..." : "Type your message..."}
        className="flex-grow"
        disabled={isProcessing}
      />
      <Button onClick={handleSend} className="ml-4" disabled={isProcessing}>
        Send
      </Button>
    </div>
  );
};
