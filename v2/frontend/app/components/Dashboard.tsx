'use client';

import React from 'react';
import { ChatInput } from './ChatInput';

export const Dashboard = () => (
  <div className="flex flex-col h-full">
    <div className="flex-grow p-4">
      {/* This is where the chat messages will go */}
    </div>
    <div className="p-4">
      <ChatInput />
    </div>
  </div>
);