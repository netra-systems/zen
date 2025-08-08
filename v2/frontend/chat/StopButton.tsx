import React from 'react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/store';
import { useWebSocket } from '@/hooks/useWebSocket';

export const StopButton: React.FC = () => {
  const { isProcessing, setProcessing } = useChatStore();
  const { sendMessage } = useWebSocket();

  const handleClick = () => {
    sendMessage(JSON.stringify({ type: 'stop_agent', payload: {} }));
    setProcessing(false);
  };

  return (
    <Button onClick={handleClick} disabled={!isProcessing} variant="destructive">
      Stop Processing
    </Button>
  );
};
