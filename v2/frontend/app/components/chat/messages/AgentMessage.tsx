import React, { useState } from 'react';
import { AgentMessage as AgentMessageProps } from '@/app/types';

const AgentMessage: React.FC<AgentMessageProps> = ({ text }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  let parsedText: any = text;
  try {
    parsedText = JSON.parse(text);
  } catch (error) {
    // Not a JSON string, treat as plain text
  }

  return (
    <div className="p-4 bg-gray-200 rounded-lg">
      {typeof parsedText === 'object' ? (
        <div>
          <button onClick={() => setIsExpanded(!isExpanded)} className="text-blue-500">
            {isExpanded ? 'Collapse' : 'Expand'} JSON
          </button>
          {isExpanded && (
            <pre className="mt-2 bg-gray-100 p-2 rounded">
              {JSON.stringify(parsedText, null, 2)}
            </pre>
          )}
        </div>
      ) : (
        <p>{text}</p>
      )}
    </div>
  );
};

export default AgentMessage;
