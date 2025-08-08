
import React from 'react';

interface ChatHeaderProps {
  subAgentName: string;
  subAgentStatus: string;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ subAgentName, subAgentStatus }) => {
  return (
    <div className="p-4 border-b">
      <h1 className="text-xl font-bold">{subAgentName}</h1>
      <p className="text-sm text-gray-500">{subAgentStatus}</p>
    </div>
  );
};

export default ChatHeader;
