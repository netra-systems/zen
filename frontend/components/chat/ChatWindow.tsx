import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useUnifiedChatStore } from '@/store/unified-chat';

export const ChatWindow = ({ onSendMessage }: { onSendMessage: (message: string) => void }) => {
  const [input, setInput] = React.useState('');
  const { isProcessing } = useUnifiedChatStore();

  const handleSend = async () => {
    if (input.trim() && !isProcessing) {
      try {
        await onSendMessage(input);
        setInput('');
      } catch (error) {
        // Handle error silently or show error message
        console.error('Failed to send message:', error);
        // Keep the input so user can retry
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div>
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message..."
        disabled={isProcessing}
      />
      <Button onClick={handleSend} disabled={isProcessing || !input.trim()}>Send</Button>
    </div>
  );
};