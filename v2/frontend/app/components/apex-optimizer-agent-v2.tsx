'use client';

import { useState } from 'react';
import { useAgent } from '../hooks/useAgent';
import { ChatMessage } from '../components/chat/ChatMessage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function ApexOptimizerAgentV2() {
  const [input, setInput] = useState('');
  const { startAgent, messages, showThinking, error } = useAgent();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim()) {
      startAgent(input);
      setInput('');
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto my-8">
      <CardHeader>
        <CardTitle>Apex Optimizer Agent V2</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col h-[600px] border rounded-lg">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {showThinking && <ChatMessage message={{id: 'thinking', role: 'agent', type: 'thinking', timestamp: new Date().toISOString()}}/>}
          </div>
          <div className="p-4 border-t">
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="Ask the agent to optimize a tool..."
                className="flex-1"
              />
              <Button type="submit">Send</Button>
            </form>
            {error && <p className="text-red-500 mt-2">{error.message}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
