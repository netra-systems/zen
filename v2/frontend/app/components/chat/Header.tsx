import React from 'react';

interface HeaderProps {
  subAgentName: string;
  agentStatus: string;
  toolInUse: string;
}

const Header: React.FC<HeaderProps> = ({ subAgentName, agentStatus, toolInUse }) => {
  return (
    <div className="p-4 border-b">
      <h1 className="text-xl font-bold">{subAgentName}</h1>
      <div className="flex space-x-4">
        <p>Status: {agentStatus}</p>
        <p>Tool: {toolInUse}</p>
      </div>
    </div>
  );
};

export default Header;
