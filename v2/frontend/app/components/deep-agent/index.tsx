
"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Terminal } from "lucide-react";
import SyntheticDataGenerator from "./synthetic-data-generator";

interface AgentStep {
  run_id: string;
  status: "in_progress" | "complete" | "failed";
  current_step: number;
  total_steps: number;
  last_step_result: any;
  final_report?: string;
}

function DeepAgentRunner({ dataSourceTable }: { dataSourceTable: string }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>("");
  const [agentState, setAgentState] = useState<AgentStep | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const startAgentRun = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v3/agent/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: `run-${Date.now()}`,
          query: prompt,
          data_source: { source_table: dataSourceTable },
          time_range: {
            start_time: new Date(Date.now() - 86400000).toISOString(),
            end_time: new Date().toISOString(),
          },
        }),
      });
      if (!response.ok) throw new Error("Failed to start agent run.");
      const data = await response.json();
      setRunId(data.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!runId || (agentState && agentState.status === "complete")) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v3/agent/${runId}/status`);
        if (!response.ok) throw new Error("Failed to fetch agent status.");
        const data: AgentStep = await response.json();
        setAgentState(data);
        if (data.status === "complete" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred.");
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [runId, agentState]);

  const progress = agentState ? (agentState.current_step / agentState.total_steps) * 100 : 0;

  return (
    <Card className="w-full max-w-2xl mx-auto mt-4">
      <CardHeader>
        <CardTitle>Deep Agent Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!runId ? (
          <div className="space-y-2">
            <Input
              placeholder="Describe your optimization goal..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isLoading}
            />
            <Button onClick={startAgentRun} disabled={isLoading || !prompt}>
              {isLoading ? "Starting..." : "Start Analysis"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium">Run ID: {runId}</p>
              <Progress value={progress} className="w-full" />
              {agentState && <p className="text-sm text-muted-foreground">Step {agentState.current_step} of {agentState.total_steps}</p>}
            </div>

            {agentState?.last_step_result && (
              <Alert>
                <Terminal className="h-4 w-4" />
                <AlertTitle>Last Step Output</AlertTitle>
                <AlertDescription>
                  <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto">
                    {JSON.stringify(agentState.last_step_result, null, 2)}
                  </pre>
                </AlertDescription>
              </Alert>
            )}

            {agentState?.status === "complete" && agentState.final_report && (
              <Alert variant="default">
                <Terminal className="h-4 w-4" />
                <AlertTitle>Analysis Complete</AlertTitle>
                <AlertDescription>
                  <pre className="text-sm whitespace-pre-wrap">{agentState.final_report}</pre>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default function DeepAgentManager() {
  const [dataSourceTable, setDataSourceTable] = useState<string | null>(null);

  return (
    <div>
      {!dataSourceTable ? (
        <SyntheticDataGenerator onGenerationComplete={setDataSourceTable} />
      ) : (
        <DeepAgentRunner dataSourceTable={dataSourceTable} />
      )}
    </div>
  );
}
