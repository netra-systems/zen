
import React from 'react';

interface AgentMessageProps {
  message: string;
}

const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  return (
    <div className="flex justify-start mb-4">
      <div className="bg-gray-200 rounded-lg p-3">
        <p>{message}</p>
      </div>
    </div>
  );
};

export default AgentMessage;
