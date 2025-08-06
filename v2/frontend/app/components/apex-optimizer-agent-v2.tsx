'use client';

import { ChatWindow } from './chat/ChatWindow';
import { useAgentStreaming } from '../hooks/useAgentStreaming';
import { getToken } from '../lib/user';
import { useState } from 'react';

import { examplePrompts } from '../lib/examplePrompts';

const exampleQueries = examplePrompts;

export default function ApexOptimizerAgentV2() {
  const { isLoading, messages, startAgent, messageFilters, setMessageFilters } = useAgentStreaming(async () => getToken());
  const [initialQuery] = useState(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);

  const handleSendMessage = async (message: string) => {
    await startAgent(message);
  };

  return (
      <ChatWindow
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        exampleQueries={exampleQueries}
        initialQuery={initialQuery}
        messageFilters={messageFilters}
        setMessageFilters={setMessageFilters}
      />
  );
}