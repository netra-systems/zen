'use client';

import { useState, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useAuth } from '@/hooks/useAuth';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { WebSocketMessage } from '@/types';

import { WEBSOCKET_URL } from '@/config';

export function Chat() {
  const [message, setMessage] = useState('');
  const [messageHistory, setMessageHistory] = useState<WebSocketMessage[]>([]);
  const { user } = useAuth();
  const socketUrl = useMemo(() => {
    if (user?.id) {
      return WEBSOCKET_URL.replace('{user_id}', user.id);
    }
    return null;
  }, [user]);

  const { sendMessage, lastMessage, readyState } = useWebSocket(socketUrl, {
    shouldReconnect: (closeEvent) => true,
  });
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
      const wsMessage: WebSocketMessage = {
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

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex-1 p-4">
        <ScrollArea className="h-full" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messageHistory.map((msg, idx) => (
              <div key={idx} className="flex items-start gap-4">
                <Avatar className="h-8 w-8">
                  {msg.picture ? (
                    <AvatarImage src={msg.picture} alt={msg.full_name} />
                  ) : (
                    <AvatarFallback>
                      {msg.full_name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')}
                    </AvatarFallback>
                  )}
                </Avatar>
                <div className="flex-1">
                  <p className="font-semibold">{msg.full_name}</p>
                  <p className="text-sm text-muted-foreground">{msg.message}</p>
                </div>
              </div>
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
          <Button onClick={handleSendMessage} disabled={readyState !== ReadyState.OPEN}>
            Send
          </Button>
        </div>
        <p className="text-xs text-center text-muted-foreground mt-2">Connection Status: {connectionStatus}</p>
      </div>
    </div>
  );
}
