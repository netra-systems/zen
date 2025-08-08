'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useChatStore } from '@/store';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message } from './Message';
import { SubAgentStatus } from './SubAgentStatus';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export const Chat = () => {
  const {
    messages,
    subAgentName,
    subAgentStatus,
    isProcessing,
    addMessage,
    setSubAgentName,
    setSubAgentStatus,
    setProcessing,
  } = useChatStore();
  const { sendMessage, lastMessage } = useWebSocket();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (lastMessage !== null) {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'message_to_user') {
        addMessage(data.payload);
      } else if (data.type === 'sub_agent_status') {
        setSubAgentName(data.payload.name);
        setSubAgentStatus(data.payload.state);
      }
    }
  }, [lastMessage, addMessage, setSubAgentName, setSubAgentStatus]);

  const handleSend = () => {
    if (input.trim()) {
      const userMessage = { content: input, sender: 'user' };
      addMessage(userMessage);
      sendMessage(JSON.stringify({ type: 'user_message', payload: userMessage }));
      setInput('');
      setProcessing(true);
    }
  };

  const handleStop = () => {
    sendMessage(JSON.stringify({ type: 'stop_agent' }));
    setProcessing(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="flex flex-col gap-4">
          {messages.map((msg, i) => (
            <Message key={i} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="p-4 border-t">
        <SubAgentStatus name={subAgentName} status={subAgentStatus} />
        <div className="flex gap-2 mt-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..."
            disabled={isProcessing}
          />
          <Button onClick={handleSend} disabled={isProcessing}>
            Send
          </Button>
          <Button onClick={handleStop} disabled={!isProcessing} variant="destructive">
            Stop
          </Button>
        </div>
      </div>
    </div>
  );
};