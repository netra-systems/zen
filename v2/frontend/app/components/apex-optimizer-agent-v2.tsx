'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useState } from 'react';
import { useAgentContext } from '@/providers/AgentProvider';
import { ChatWindow } from './chat/ChatWindow';
import LoginButton from './LoginButton';
import { examplePrompts } from '@/lib/examplePrompts';
import { MessageFilter, WebSocketMessage, AnalysisRequest } from '@/types';
import useAppStore from '@/store';

export function ApexOptimizerAgentV2() {
  const { messages, showThinking, error, sendWsMessage } = useAgentContext();
  const [messageFilters, setMessageFilters] = useState<MessageFilter>({ 
    event: false, 
    thinking: true 
  });
  const { user } = useAppStore();

  const handleSendMessage = (message: string) => {
    if (!user) {
      console.error('User is not logged in.');
      return;
    }

    const analysisRequest: AnalysisRequest = {
      settings: {
        debug_mode: true,
      },
      request: {
        user_id: user.id.toString(),
        query: message,
        workloads: [],
        references: [],
      },
    };

    const wsMessage: WebSocketMessage = {
      type: 'analysis_request',
      payload: analysisRequest,
    };

    sendWsMessage(wsMessage);
  };

  return (
    <Card className="w-full h-full flex flex-col" role="article">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Apex Optimizer Agent</CardTitle>
        <LoginButton />
      </CardHeader>
      <CardContent className="flex-grow overflow-y-auto">
        <ChatWindow 
          messages={messages}
          onSendMessage={handleSendMessage}
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