import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export const ChatWindow = ({ onSendMessage }) => {
  const [input, setInput] = React.useState('');

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div>
      <Input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Type your message..."
      />
      <Button onClick={handleSend}>Send</Button>
    </div>
  );
};