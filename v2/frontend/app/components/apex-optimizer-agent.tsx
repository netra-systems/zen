
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/button';
import { Input } from '@/components/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/card';
import { Progress } from '@/components/progress';
import { Switch } from '@/components/switch';
import { Label } from '@/components/label';

const exampleQueries = [
  "Analyze the current state of the S&P 500 and provide a summary of its recent performance.",
  "What are the latest trends in the technology sector, and which stocks are leading the way?",
  "Provide a detailed analysis of the real estate market in California, including key metrics and forecasts.",
  "Compare the financial performance of Apple and Microsoft over the last five years.",
  "What is the outlook for the energy sector, considering recent geopolitical events?",
  "Analyze the impact of inflation on consumer spending and the retail industry.",
  "What are the most promising emerging markets for investment right now?"
];

export default function DeepAgent() {
  const [runId, setRunId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);
  const [status, setStatus] = useState<string | null>(null);
  const [step, setStep] = useState<number>(0);
  const [totalSteps, setTotalSteps] = useState<number>(0);
  const [lastStepResult, setLastStepResult] = useState<any | null>(null);
  const [completedSteps, setCompletedSteps] = useState<any[]>([]);
  const [finalReport, setFinalReport] = useState<string | null>(null);
  const [isAutoProgress, setIsAutoProgress] = useState<boolean>(false);

  const startAnalysis = async () => {
    const response = await fetch('/api/v3/agent/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: prompt, run_id: `run-${Date.now()}` }),
    });
    const data = await response.json();
    setRunId(data.run_id);
    setCompletedSteps([]);
  };

  const handleNextStep = async () => {
    if (!runId) return;
    const response = await fetch(`/api/v3/agent/${runId}/next`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation: true }),
    });
    const data = await response.json();
    setLastStepResult(data.result);
    if (data.completed_step) {
      setCompletedSteps(prev => [...prev, { step: data.completed_step, result: data.result }]);
    }
  };

  const handleClear = () => {
    setPrompt('');
  };

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        const response = await fetch(`/api/v3/agent/${runId}/status`);
        const data = await response.json();
        setStatus(data.status);
        setStep(data.current_step);
        setTotalSteps(data.total_steps);
        setLastStepResult(data.last_step_result);

        if (data.status === 'complete') {
          setFinalReport(data.final_report);
          clearInterval(interval);
        } else if (isAutoProgress && data.status === 'awaiting_confirmation') {
          handleNextStep();
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [runId, isAutoProgress]);

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
          <Button onClick={startAnalysis}>Start Analysis</Button>
          <Button onClick={handleClear} variant="outline">Clear</Button>
        </div>
        <div className="flex items-center space-x-2">
          <Switch id="auto-progress" checked={isAutoProgress} onCheckedChange={setIsAutoProgress} />
          <Label htmlFor="auto-progress">Auto-progress</Label>
        </div>
        {runId && (
          <div>
            <p>Run ID: {runId}</p>
            <p>Status: {status}</p>
            <Progress value={(step / totalSteps) * 100} />
            <p>
              Step {step} of {totalSteps}
            </p>
            {status === 'awaiting_confirmation' && !isAutoProgress && (
              <Button onClick={handleNextStep} className="mt-2">Confirm & Continue</Button>
            )}
          </div>
        )}
        {completedSteps.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mt-4">Analysis History</h2>
            <div className="space-y-4 mt-2">
              {completedSteps.map((item, index) => (
                <Card key={index}>
                  <CardHeader>
                    <CardTitle>Step {index + 1}: {item.step}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="bg-gray-100 p-2 rounded-md">{JSON.stringify(item.result, null, 2)}</pre>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
        {finalReport && (
          <div>
            <h2 className="text-lg font-semibold mt-4">Final Report</h2>
            <pre className="bg-gray-100 p-4 rounded-md">{finalReport}</pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
