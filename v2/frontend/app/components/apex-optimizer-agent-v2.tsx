'use client';

import { useState } from 'react';
import { useAgent } from '../hooks/useAgent';
import { ChatMessage } from '../components/chat/ChatMessage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const examplePrompts = [
  "Analyze the 'fetch_user_data' tool and suggest optimizations.",
  "How can I improve the performance of the 'process_image' tool?",
  "Find bottlenecks in the 'run_simulation' tool.",
  "What are the cost drivers for the 'generate_report' tool?",
];

const truncatePrompt = (prompt: string, maxLength: number) => {
  const words = prompt.split(' ');
  if (words.length > maxLength) {
    return words.slice(0, maxLength).join(' ') + '...';
  }
  return prompt;
};

export default function ApexOptimizerAgentV2() {
  const [input, setInput] = useState('');
  const { startAgent, messages, showThinking, error } = useAgent();
  const [showExamples, setShowExamples] = useState(true);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (input.trim()) {
      startAgent(input);
      setInput('');
      setShowExamples(false);
    }
  };

  const handleExampleClick = (prompt: string) => {
    setInput(prompt);
    setShowExamples(false);
  };

  return (
    <Card className="w-full max-w-4xl mx-auto my-8" role="article">
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
            {showExamples && (
              <Card className="mb-4">
                <CardHeader>
                  <CardTitle>Example Prompts</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-4">
                  {examplePrompts.map((prompt, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      onClick={() => handleExampleClick(prompt)}
                      className="text-left h-auto"
                      className="text-left whitespace-normal min-h-[4rem]"
                    >
                    </Button>
                  ))}
                </CardContent>
              </Card>
            )}
            <form onSubmit={handleSubmit} className="flex items-center gap-2" role="form">
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