import React from 'react';
import { useChatStore } from '@/store/chat';
import { Bot, Zap, Terminal } from 'lucide-react';

export const ChatHeader: React.FC = () => {
  const { subAgentName, subAgentStatus } = useChatStore();

  return (
    <div className="p-4 border-b bg-gray-50 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Bot className="w-6 h-6 mr-3 text-blue-500" />
          <h1 className="text-2xl font-bold text-gray-800">{subAgentName}</h1>
        </div>
        {subAgentStatus && (
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-600">
              <Zap className="w-4 h-4 mr-1.5 text-yellow-500" />
              <span>{subAgentStatus.status}</span>
            </div>
            {subAgentStatus.tools && subAgentStatus.tools.length > 0 && (
              <div className="flex items-center text-sm text-gray-600">
                <Terminal className="w-4 h-4 mr-1.5 text-green-500" />
                <span>Tools: {subAgentStatus.tools.join(', ')}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};