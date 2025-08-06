
'use client';

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { ChatWindow } from './chat/ChatWindow';
import { useAgentStreaming } from '../hooks/useAgentStreaming';

const exampleQueries = [
  "Analyze the current state of the S&P 500 and provide a summary of its recent performance.",
  "What are the latest trends in the technology sector, and which stocks are leading the way?",
  "Provide a detailed analysis of the real estate market in California, including key metrics and forecasts.",
  "Compare the financial performance of Apple and Microsoft over the last five years.",
  "What is the outlook for the energy sector, considering recent geopolitical events?",
  "Analyze the impact of inflation on consumer spending and the retail industry.",
  "What are the most promising emerging markets for investment right now?"
];

export default function ApexOptimizerAgentV2() {
  const { getToken } = useAuth();
  const { isLoading, error, messages, startAgent } = useAgentStreaming(getToken);

  const handleSendMessage = async (message: string) => {
    await startAgent(message);
  };

  return (
      <ChatWindow
        messages={messages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        exampleQueries={exampleQueries}
      />
  );
}
