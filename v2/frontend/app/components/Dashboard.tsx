'use client';

import React from 'react';
import { ChatInput } from './ChatInput';
import { ChatHistory } from './ChatHistory';
import { useAgent } from '../hooks/useAgent';

export const Dashboard = () => {
  const { messages, startAgent, isConnected } = useAgent();

  return (
    <div className="flex flex-col h-full items-center justify-center">
      <div className="w-full max-w-2xl flex flex-col h-full">
        <ChatHistory messages={messages} />
        <div className="mt-4">
          <ChatInput onSendMessage={startAgent} />
        </div>
        <div className="flex justify-center space-x-4 mt-4">
          <p className="text-sm text-gray-500">
            WebSocket status: {isConnected ? 'Connected' : 'Disconnected'}
          </p>
        </div>
      </div>
    </div>
  );
};