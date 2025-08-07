
'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useState } from 'react';
import { MessageFactory } from '../services/agent/MessageFactory';
import { useAgentContext } from '../providers/AgentProvider';
import { MessageOrchestrator } from './chat/MessageOrchestrator';
import LoginButton from './LoginButton';

const examplePrompts = [
  'Analyze the latency of the `get_user_data` tool and suggest optimizations.',
    'Find the most expensive tool in my project and explain why it is so costly.',
  'Simulate the cost impact of a 50% increase in traffic to the `process_payment` tool.',
  'Generate a report on the quality of the `generate_report` tool.',
];

function truncatePrompt(prompt: string, words: number) {
  return prompt.split(' ').slice(0, words).join(' ') + '...';
}

export default function ApexOptimizerAgentV2() {
  const { messages, showThinking, startAgent, error } = useAgentContext();
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      startAgent(inputValue);
      setInputValue('');
    }
  };

  const handleExampleQuery = (prompt: string) => {
    setInputValue(prompt);
  };

  return (
    <Card className="w-full h-full flex flex-col" role="article">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Apex Optimizer Agent</CardTitle>
        <LoginButton />
      </CardHeader>
      <CardContent className="flex-grow overflow-y-auto">
        <MessageOrchestrator messages={messages} showThinking={showThinking} error={error} />
      </CardContent>
      <div className="p-4 border-t">
        <div className="grid grid-cols-2 gap-2 mb-4">
          {examplePrompts.map((prompt) => (
            <Button key={prompt} variant="outline" onClick={() => handleExampleQuery(prompt)}>
              {truncatePrompt(prompt, 5)}
            </Button>
          ))}
        </div>
        <form onSubmit={handleSendMessage} className="flex gap-2" role="form">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask the agent to optimize a tool..."
          />
          <Button type="submit">Send</Button>
        </form>
      </div>
    </Card>
  );
}
