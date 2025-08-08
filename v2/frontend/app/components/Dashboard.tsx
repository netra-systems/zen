'use client';

import React, { useState } from 'react';
import { ChatInput } from './ChatInput';
import { ChatHistory } from './ChatHistory';
import { useAgentContext } from '../providers/AgentProvider';
import { MessageFilter } from './MessageFilter';
import { Message, WebSocketStatus } from '@/types/index';

export const Dashboard = () => {
  const { messages, startAgent, wsStatus } = useAgentContext();
  const [filter, setFilter] = useState('all');

  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
  };

  const filteredMessages = messages.filter((message: Message) => {
    if (filter === 'all') {
      return true;
    }
    return message.role === filter;
  });

  return (
    <div className="flex flex-col h-full items-center justify-center">
      <div className="w-full max-w-2xl flex flex-col h-full">
        <MessageFilter onFilterChange={handleFilterChange} />
        <ChatHistory messages={filteredMessages} />
        <div className="mt-4">
          <ChatInput onSendMessage={startAgent} />
        </div>
        <div className="flex justify-center space-x-4 mt-4">
          <p className="text-sm text-gray-500">
            WebSocket status: {wsStatus === WebSocketStatus.Open ? 'Connected' : 'Disconnected'}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;