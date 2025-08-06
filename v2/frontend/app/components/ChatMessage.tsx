
'use client';

import { useState } from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [showThinking, setShowThinking] = useState(false);
  const [showJson, setShowJson] = useState(false);

  const toggleThinking = () => setShowThinking(!showThinking);
  const toggleJson = () => setShowJson(!showJson);

  const formatContent = (content: string) => {
    const eventRegex = /event: ({.*})/g;
    let match;
    const parts = [];
    let lastIndex = 0;

    while ((match = eventRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      const json = JSON.parse(match[1]);
      parts.push(
        <div key={match.index}>
          <button onClick={toggleJson} className="text-blue-500 hover:underline">
            {showJson ? 'Hide JSON' : 'Show JSON'}
          </button>
          {showJson && (
            <pre className="bg-gray-100 p-2 rounded">
              {JSON.stringify(json, null, 2)}
            </pre>
          )}
        </div>
      );
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className={`my-2 p-2 rounded-lg ${message.role === 'user' ? 'bg-blue-100' : 'bg-gray-100'}`}>
      <div className="font-bold">{message.role}</div>
      <div>
        {message.role === 'assistant' && (
          <button onClick={toggleThinking} className="text-blue-500 hover:underline">
            {showThinking ? 'Hide Thinking' : 'Show Thinking'}
          </button>
        )}
      </div>
      {showThinking || message.role === 'user' ? (
        <div>{formatContent(message.content)}</div>
      ) : (
        <div>{message.content.split('event:')[0]}</div>
      )}
    </div>
  );
}
