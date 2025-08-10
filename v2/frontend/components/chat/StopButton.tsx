import React from 'react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/store/chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Square } from 'lucide-react';

export const StopButton: React.FC = () => {
  const { isProcessing, setProcessing } = useChatStore();
  const { sendMessage } = useWebSocket();

  const handleClick = () => {
    sendMessage({ type: 'stop_agent', payload: {} });
    setProcessing(false);
  };

  return (
    <Button onClick={handleClick} disabled={!isProcessing} variant="destructive" className="mt-4 w-full flex items-center">
      <Square className="w-4 h-4 mr-2" />
      Stop Processing
    </Button>
  );
};