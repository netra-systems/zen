import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { Send } from 'lucide-react';

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
    <div className="flex items-center">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder={isProcessing ? 'Agent is thinking...' : 'Type your message...'}
        className="flex-grow rounded-full py-2 px-4 bg-gray-100 focus:bg-white focus:ring-2 focus:ring-blue-500 transition-all duration-300"
        disabled={isProcessing}
      />
      <Button onClick={handleSend} className="ml-4 rounded-full w-12 h-12 flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white" disabled={isProcessing} aria-label="Send">
        <Send className="w-6 h-6" />
      </Button>
    </div>
  );
};