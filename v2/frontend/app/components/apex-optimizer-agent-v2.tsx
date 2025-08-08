'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { useAgentContext } from '../providers/AgentProvider';
import { ChatWindow } from './chat/ChatWindow';
import LoginButton from './LoginButton';
import { examplePrompts } from '../lib/examplePrompts';
import { MessageFilter } from '../types';

export function ApexOptimizerAgentV2() {
  const { messages, showThinking, startAgent, error } = useAgentContext();
  const [messageFilters, setMessageFilters] = useState<MessageFilter>({ 
    event: false, 
    thinking: true 
  });

  return (
    <Card className="w-full h-full flex flex-col" role="article">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Apex Optimizer Agent</CardTitle>
        <LoginButton />
      </CardHeader>
      <CardContent className="flex-grow overflow-y-auto">
        <ChatWindow 
          messages={messages}
          onSendMessage={startAgent}
          isLoading={showThinking}
          messageFilters={messageFilters}
          setMessageFilters={setMessageFilters}
          exampleQueries={examplePrompts}
        />
        {error && <div className="text-red-500 p-4">{error.message}</div>}
      </CardContent>
    </Card>
  );
}

export default ApexOptimizerAgentV2;