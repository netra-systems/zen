'use client';

import { ChatWindow } from './chat/ChatWindow';
import { useAgent } from '../hooks/useAgent';
import { useState } from 'react';

import { examplePrompts } from '../lib/examplePrompts';

const exampleQueries = examplePrompts;

export default function ApexOptimizerAgentV2() {
  const { messages, messageFilters, setMessageFilters, showThinking, startAgent } = useAgent();
  const [initialQuery] = useState(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);

  const handleSendMessage = async (message: string) => {
    await startAgent(message);
  };

  return (
      <ChatWindow
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={showThinking}
        exampleQueries={exampleQueries}
        initialQuery={initialQuery}
        messageFilters={messageFilters}
        setMessageFilters={setMessageFilters}
      />
  );
}