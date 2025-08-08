import React from 'react';
import { ToolStarted, ToolCompleted } from '@/app/types';

interface ToolMessageProps {
  message: ToolStarted | ToolCompleted;
}

const ToolMessage: React.FC<ToolMessageProps> = ({ message }) => {
  return (
    <div className="p-4 bg-yellow-100 rounded-lg">
      <p className="font-bold">Tool: {message.tool_name}</p>
      {message.type === 'tool_completed' && (
        <pre className="mt-2 bg-gray-100 p-2 rounded">
          {JSON.stringify(message.result, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default ToolMessage;
