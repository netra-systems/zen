'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAgentPolling } from '../hooks/useAgentPolling';
import { useAuth } from '@clerk/nextjs';
import { apiService } from '../api';

const exampleQueries = [
  "Analyze the current state of the S&P 500 and provide a summary of its recent performance.",
  "What are the latest trends in the technology sector, and which stocks are leading the way?",
  "Provide a detailed analysis of the real estate market in California, including key metrics and forecasts.",
  "Compare the financial performance of Apple and Microsoft over the last five years.",
  "What is the outlook for the energy sector, considering recent geopolitical events?",
  "Analyze the impact of inflation on consumer spending and the retail industry.",
  "What are the most promising emerging markets for investment right now?"
];

export default function ApexOptimizerAgent() {
  const { getToken } = useAuth();
  const [prompt, setPrompt] = useState<string>(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);
  const { messages, addMessage, startPolling, isLoading, error } = useAgentPolling(getToken());

  const startAnalysis = async () => {
    addMessage('user', prompt);
    const body = { prompt };
    const runId = await apiService.startAgent(await getToken(), body);
    startPolling(runId.run_id);
  };

  const handleClear = () => {
    setPrompt('');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Apex Optimizer Agent Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-2">
          <Input
            placeholder="Enter your analysis prompt..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="flex-grow"
          />
          <Button onClick={startAnalysis} disabled={isLoading}>Start Analysis</Button>
          <Button onClick={handleClear} variant="outline">Clear</Button>
        </div>
        {error && (
          <div className="text-red-500">
            <p>Error: {error.message}</p>
          </div>
        )}
        <div className="space-y-4 mt-2">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`p-2 rounded-md ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}>
                {msg.content}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}