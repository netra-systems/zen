'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/hooks/useAuth';
import { useWebSocket } from '@/hooks/useWebSocket';
import { MessageCard } from '@/components/MessageCard';
import { Message } from '@/types/chat';
import { WEBSOCKET_URL } from '@/config';

export function Chat() {
  const [message, setMessage] = useState('');
  const { user } = useAuth();
  const socketUrl = useMemo(() => {
    if (user?.id) {
      return WEBSOCKET_URL.replace('{user_id}', user.id);
    }
    return null;
  }, [user]);

  const { lastMessage, readyState, sendMessage, subAgentName, subAgentStatus } = useWebSocket(socketUrl, {
    shouldReconnect: (closeEvent) => true,
  });
  const [messageHistory, setMessageHistory] = useState<Message[]>([]);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (lastMessage !== null) {
      const parsedMessage = JSON.parse(lastMessage.data);
      setMessageHistory((prev) => [...prev, parsedMessage]);
    }
  }, [lastMessage]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTo({ top: scrollAreaRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [messageHistory]);

  const handleSendMessage = () => {
    if (message.trim()) {
      const wsMessage: Message = {
        id: new Date().toISOString(),
        type: 'user',
        user_id: user?.id || 'anonymous',
        message: message,
        timestamp: new Date().toISOString(),
        full_name: user?.full_name || 'Anonymous',
        picture: user?.picture || undefined,
      };
      sendMessage(JSON.stringify(wsMessage));
      setMessage('');
    }
  };

  const handleStop = () => {
    const wsMessage = {
      type: 'stop',
    };
    sendMessage(JSON.stringify(wsMessage));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h2 className="text-lg font-semibold">{subAgentName}</h2>
          <p className="text-sm text-muted-foreground">{subAgentStatus}</p>
        </div>
        <Button onClick={handleStop} variant="destructive">Stop</Button>
      </div>
      <div className="flex-1 p-4">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messageHistory.map((msg) => (
              <MessageCard key={msg.id} message={msg} />
            ))}
          </div>
        </ScrollArea>
      </div>
      <div className="p-4 border-t">
        <div className="flex items-center gap-4">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
          />
          <Button onClick={handleSendMessage} disabled={readyState !== 'OPEN'}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
