import React from 'react';
import { useChatStore } from '@/store';

export const ChatHeader: React.FC = () => {
  const { subAgentName, subAgentStatus } = useChatStore();

  return (
    <div className="p-4 border-b">
      <h1 className="text-xl font-bold">{subAgentName}</h1>
      <p className="text-sm text-gray-500">{subAgentStatus?.status}</p>
      {subAgentStatus?.tools && (
        <p className="text-sm text-gray-500">Tools: {subAgentStatus.tools.join(', ')}</p>
      )}
    </div>
  );
};
