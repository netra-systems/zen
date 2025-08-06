'use client';

import { ChatWindow } from './chat/ChatWindow';
import { useAgentStreaming } from '../hooks/useAgentStreaming';
import { getToken } from '../lib/user';
import { useState } from 'react';

import { examplePrompts } from '../lib/examplePrompts';

const exampleQueries = examplePrompts;

export default function ApexOptimizerAgentV2() {
  const { messages, addMessage, messageFilters, setMessageFilters, showThinking, processStream } = useAgentStreaming();
  const [initialQuery] = useState(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);

  const handleSendMessage = async (message: string) => {
    addMessage(message);
    const token = await getToken();
    // TODO: Call the agent with the token and message
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
