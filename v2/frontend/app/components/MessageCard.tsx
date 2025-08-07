'use client';

import { useState } from 'react';
import { Message } from '../types';
import { ArtifactRenderer } from './ArtifactRenderer';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

interface MessageCardProps {
  message: Message;
  user: {
    name: string;
    picture: string;
  }
}

export function MessageCard({ message, user }: MessageCardProps) {
  const [showThinking, setShowThinking] = useState(false);

  const toggleThinking = () => setShowThinking(!showThinking);

  return (
    <div
      className={`flex items-start gap-4 ${
        message.role === 'user' ? 'justify-end' : ''
      }`}
    >
      {message.role === 'assistant' && (
        <Avatar>
          <AvatarImage src="/agent-avatar.png" />
          <AvatarFallback>A</AvatarFallback>
        </Avatar>
      )}
      <div
        className={`rounded-lg p-3 max-w-[75%] ${
          message.role === 'user'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        }`}
      >
        <p className="text-sm">{message.content}</p>
        {message.artifact && <ArtifactRenderer artifact={message.artifact} />}
        {message.role === 'assistant' && (
          <div>
            <button onClick={toggleThinking} className="text-blue-500 hover:underline mt-2">
              {showThinking ? 'Hide Thinking' : 'Show Thinking'}
            </button>
            {showThinking && (
              <div className="mt-2">
                <JsonView data={message} shouldExpandNode={allExpanded} style={defaultStyles} />
              </div>
            )}
          </div>
        )}
      </div>
      {message.role === 'user' && (
        <Avatar>
          <AvatarImage src={user.picture} />
          <AvatarFallback>
            {user.name.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
