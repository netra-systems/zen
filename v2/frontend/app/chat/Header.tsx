"use client";

import React from 'react';
import { useChatStore } from '../store';

const Header: React.FC = () => {
  const { subAgentName, subAgentStatus } = useChatStore();

  return (
    <div className="p-4 border-b">
      <h1 className="text-xl font-bold">{subAgentName}</h1>
      <p className="text-sm text-gray-500">{subAgentStatus}</p>
    </div>
  );
};

export default Header;