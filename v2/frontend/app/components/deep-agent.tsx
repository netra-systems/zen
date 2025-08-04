
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

export default function DeepAgent() {
  const [runId, setRunId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [status, setStatus] = useState<string | null>(null);
  const [step, setStep] = useState<number>(0);
  const [totalSteps, setTotalSteps] = useState<number>(0);
  const [history, setHistory] = useState<any | null>(null);
  const [finalReport, setFinalReport] = useState<string | null>(null);

  const startAnalysis = async () => {
    const response = await fetch('/api/v3/agent/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: prompt, run_id: `run-${Date.now()}` }),
    });
    const data = await response.json();
    setRunId(data.run_id);
  };

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        const response = await fetch(`/api/v3/agent/${runId}/step`);
        const data = await response.json();
        setStatus(data.status);
        setStep(data.current_step);
        setTotalSteps(data.total_steps);
        if (data.status === 'complete') {
          setFinalReport(data.final_report);
          const historyResponse = await fetch(`/api/v3/agent/${runId}/history`);
          const historyData = await historyResponse.json();
          setHistory(historyData.history);
          clearInterval(interval);
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [runId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deep Agent Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Input
            placeholder="Enter your analysis prompt..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <Button onClick={startAnalysis}>Start Analysis</Button>
          {runId && (
            <div>
              <p>Status: {status}</p>
              <Progress value={(step / totalSteps) * 100} />
              <p>
                Step {step} of {totalSteps}
              </p>
            </div>
          )}
          {finalReport && (
            <div>
              <h2>Final Report</h2>
              <pre>{finalReport}</pre>
            </div>
          )}
          {history && (
            <div>
              <h2>History</h2>
              <pre>{JSON.stringify(history, null, 2)}</pre>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
