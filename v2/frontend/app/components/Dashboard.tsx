import React from 'react';
import { ChatInput } from './ChatInput';

export const Dashboard = () => (
  <div className="flex flex-col h-full items-center justify-center">
    <div className="w-full max-w-2xl">
      <ChatInput />
      <div className="flex justify-center space-x-4 mt-4">
        <p className="text-sm text-gray-500">@frontend/.next/server/server-reference-manifest.js</p>
      </div>
    </div>
  </div>
);