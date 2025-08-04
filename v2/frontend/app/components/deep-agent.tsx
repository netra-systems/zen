
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/label';

export default function DeepAgent() {
  const [runId, setRunId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
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

  useEffect(() => {
    if (runId) {
      const interval = setInterval(async () => {
        const response = await fetch(`/api/v3/agent/${runId}/step`);
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
        <CardTitle>Deep Agent Analysis</CardTitle>
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
