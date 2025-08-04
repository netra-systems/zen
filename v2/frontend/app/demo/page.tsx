'use client';

import React, { useState, FormEvent, useEffect, useCallback } from 'react';
import { Play, Pause, FastForward, ChevronRight, ChevronDown, CheckCircle, XCircle, Loader, Settings, BarChart2, ThumbsUp, ThumbsDown } from 'lucide-react';

import { config } from '../config';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { GenericInput } from '@/components/GenericInput';
import useAppStore from '../store';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/card';
import { Button } from '@/components/button';
import { Progress } from '@/components/ui/progress';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// --- API Service ---
const apiService = {
    async get(endpoint: string, token: string | null) {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
            throw new Error(errorData.detail);
        }
        return response.json();
    },
    async post(endpoint: string, body: Record<string, unknown>, token: string | null) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
            throw new Error(errorData.detail);
        }
        return response.json();
    }
};

// --- Types ---
interface SyntheticDataParams {
    num_traces: number;
    num_users: number;
    error_rate: number;
    event_types: string;
}

interface AgentStep {
    run_id: string;
    status: 'in_progress' | 'complete' | 'failed' | 'awaiting_confirmation';
    current_step: number;
    total_steps: number;
    last_step_result: any;
    final_report?: string;
}

interface AgentHistory {
    run_id: string;
    is_complete: boolean;
    history: any;
}

const DEMO_PROMPTS = [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
];

// --- Main Component ---
export default function DemoPage() {
    const { token } = useAppStore();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [runId, setRunId] = useState<string | null>(null);
    const [agentState, setAgentState] = useState<AgentStep | null>(null);
    const [agentHistory, setAgentHistory] = useState<AgentHistory | null>(null);
    const [autoProgress, setAutoProgress] = useState(true);

    const [dataParams, setDataParams] = useState<SyntheticDataParams>({
        num_traces: 1000,
        num_users: 100,
        error_rate: 0.05,
        event_types: 'search, login, purchase, logout',
    });
    const [analysisQuery, setAnalysisQuery] = useState(DEMO_PROMPTS[0]);

    const pollAgentStatus = useCallback(async (currentRunId: string) => {
        if (!token) return;
        try {
            const state = await apiService.get(`${config.api.baseUrl}/api/v3/agent/${currentRunId}/step`, token);
            setAgentState(state);
            if (state.status === 'complete') {
                const history = await apiService.get(`${config.api.baseUrl}/api/v3/agent/${currentRunId}/history`, token);
                setAgentHistory(history);
                setIsLoading(false);
            } else if (autoProgress && state.status !== 'awaiting_confirmation') {
                // Continue polling if auto-progress is on
                setTimeout(() => pollAgentStatus(currentRunId), 2000);
            }
        } catch (err) {
            console.error("Error polling agent status:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
            setIsLoading(false);
        }
    }, [token, autoProgress]);

    const handleStartAnalysis = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);
        setRunId(null);
        setAgentState(null);
        setAgentHistory(null);

        try {
            // Step 1: Generate Synthetic Data
            const dataGenResponse = await apiService.post(`${config.api.baseUrl}/api/v3/generation/synthetic_data`, {
                ...dataParams,
                event_types: dataParams.event_types.split(',').map(s => s.trim()),
            }, token);

            // For this demo, we'll assume the data is ready and proceed.
            // In a real app, you'd poll the generation job status.

            // Step 2: Create and Start the Agent Run
            const agentRequest = {
                run_id: `run-${Date.now()}`,
                query: analysisQuery,
                data_source: {
                    source_table: "default.synthetic_data", // Use the table where data was generated
                    filters: {}
                },
                time_range: {
                    start_time: new Date(Date.now() - 86400000).toISOString(), // last 24 hours
                    end_time: new Date().toISOString()
                }
            };

            const agentResponse = await apiService.post(`${config.api.baseUrl}/api/v3/agent/create`, agentRequest, token);
            const newRunId = agentResponse.run_id;
            setRunId(newRunId);

            // Start polling for status
            pollAgentStatus(newRunId);

        } catch (err: unknown) {
            console.error("Error starting analysis:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
            setIsLoading(false);
        }
    };

    const handleNextStep = async (confirmation: boolean) => {
        if (!runId || !token) return;
        setIsLoading(true);
        try {
            const state = await apiService.post(`${config.api.baseUrl}/api/v3/agent/${runId}/next`, { confirmation }, token);
            setAgentState(state);
            if (state.status === 'complete') {
                const history = await apiService.get(`${config.api.baseUrl}/api/v3/agent/${runId}/history`, token);
                setAgentHistory(history);
                setIsLoading(false);
            } else {
                 // If not on auto-progress, we need to manually poll again after triggering next step
                if (!autoProgress) {
                    setTimeout(() => pollAgentStatus(runId), 1000);
                }
            }
        } catch (err) {
            console.error("Error triggering next step:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCancelAnalysis = () => {
        // In a real application, you would call an API endpoint to cancel the run.
        // For this demo, we'll just reset the state.
        setRunId(null);
        setAgentState(null);
        setAgentHistory(null);
        setError(null);
        setIsLoading(false);
    };

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <Header />
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
                    <h1 className="text-2xl font-semibold">Deep Agent Demo</h1>
                    {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative mb-6" role="alert">{error}</div>}

                    <Tabs defaultValue="analysis">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="analysis"><BarChart2 className="mr-2 h-4 w-4" />Analysis</TabsTrigger>
                            <TabsTrigger value="settings"><Settings className="mr-2 h-4 w-4" />Settings</TabsTrigger>
                        </TabsList>
                        <TabsContent value="analysis">
                            <Card>
                                <form onSubmit={handleStartAnalysis}>
                                    <CardHeader>
                                        <CardTitle>Start New Analysis</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div>
                                            <label htmlFor="analysisQuery" className="block text-sm font-medium text-gray-700">Select a Demo Scenario</label>
                                            <select
                                                id="analysisQuery"
                                                value={analysisQuery}
                                                onChange={(e) => setAnalysisQuery(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                                            >
                                                {DEMO_PROMPTS.map((prompt, index) => (
                                                    <option key={index} value={prompt}>{prompt}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </CardContent>
                                    <CardFooter>
                                        <Button type="submit" disabled={isLoading}>
                                            {isLoading ? <><Loader className="mr-2 h-4 w-4 animate-spin" /> Starting...</> : 'Run Analysis'}
                                        </Button>
                                    </CardFooter>
                                </form>
                            </Card>
                        </TabsContent>
                        <TabsContent value="settings">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Synthetic Data Generation</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <GenericInput
                                        title=""
                                        description="Configure the parameters for generating synthetic log data for the analysis."
                                        inputFields={[
                                            { id: 'num_traces', name: 'num_traces', label: 'Number of Traces', type: 'number', required: true, defaultValue: dataParams.num_traces },
                                            { id: 'num_users', name: 'num_users', label: 'Number of Users', type: 'number', required: true, defaultValue: dataParams.num_users },
                                            { id: 'error_rate', name: 'error_rate', label: 'Error Rate (0.0 to 1.0)', type: 'number', required: true, defaultValue: dataParams.error_rate },
                                            { id: 'event_types', name: 'event_types', label: 'Event Types (comma-separated)', type: 'text', required: true, defaultValue: dataParams.event_types },
                                        ]}
                                        onSubmit={(e) => {
                                            e.preventDefault();
                                            const formData = new FormData(e.target as HTMLFormElement);
                                            setDataParams({
                                                num_traces: Number(formData.get('num_traces')),
                                                num_users: Number(formData.get('num_users')),
                                                error_rate: Number(formData.get('error_rate')),
                                                event_types: formData.get('event_types') as string,
                                            });
                                        }}
                                        submitButtonText="Save Settings"
                                    />
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>

                    {runId && (
                        <Card className="mt-8">
                            <CardHeader>
                                <CardTitle>Analysis Progress (Run ID: {runId})</CardTitle>
                                <div className="flex items-center space-x-4 pt-2">
                                    <Button variant="outline" size="sm" onClick={() => setAutoProgress(!autoProgress)} disabled={agentState?.status === 'complete'}>
                                        {autoProgress ? <><Pause className="mr-2 h-4 w-4" /> Auto-Progress ON</> : <><Play className="mr-2 h-4 w-4" /> Auto-Progress OFF</>}
                                    </Button>
                                    {!autoProgress && (
                                        <Button size="sm" onClick={() => handleNextStep(true)} disabled={isLoading || agentState?.status === 'complete' || agentState?.status === 'awaiting_confirmation'}>
                                            <FastForward className="mr-2 h-4 w-4" /> Next Step
                                        </Button>
                                    )}
                                    <Button variant="destructive" size="sm" onClick={handleCancelAnalysis} disabled={agentState?.status === 'complete'}>
                                        <XCircle className="mr-2 h-4 w-4" /> Cancel
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                {agentState && (
                                    <div>
                                        <Progress value={(agentState.current_step / agentState.total_steps) * 100} className="w-full" />
                                        <p className="text-sm text-muted-foreground mt-2">
                                            Step {agentState.current_step} of {agentState.total_steps}: {agentState.status}
                                        </p>
                                        <div className="mt-4 p-4 bg-gray-50 rounded-md border">
                                            <h3 className="font-semibold">Last Step Result:</h3>
                                            <pre className="mt-2 bg-gray-100 text-gray-800 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                                                <code>{JSON.stringify(agentState.last_step_result, null, 2)}</code>
                                            </pre>
                                            {agentState.status === 'awaiting_confirmation' && (
                                                <div className="mt-4 flex space-x-4">
                                                    <Button size="sm" onClick={() => handleNextStep(true)} disabled={isLoading}>
                                                        <ThumbsUp className="mr-2 h-4 w-4" /> Confirm & Proceed
                                                    </Button>
                                                    <Button size="sm" variant="outline" onClick={() => handleNextStep(false)} disabled={isLoading}>
                                                        <ThumbsDown className="mr-2 h-4 w-4" /> Reject & Modify
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                                {agentState?.status === 'complete' && agentHistory && (
                                    <div className="mt-6">
                                        <h3 className="text-lg font-semibold">Final Report & Playback</h3>
                                        <Card className="mt-2">
                                            <CardHeader><CardTitle>Report</CardTitle></CardHeader>
                                            <CardContent>
                                                <p className="text-sm">{agentState.final_report}</p>
                                            </CardContent>
                                        </Card>
                                        <Accordion type="single" collapsible className="w-full mt-4">
                                            <AccordionItem value="item-1">
                                                <AccordionTrigger>Show Execution Playback</AccordionTrigger>
                                                <AccordionContent>
                                                    {Object.entries(agentHistory.history).map(([key, value]) => (
                                                        <div key={key} className="text-xs p-2 border-b">
                                                            <p className="font-bold">{key}:</p>
                                                            <pre className="mt-1 bg-gray-100 text-gray-800 rounded-md p-2 font-mono">
                                                                <code>{JSON.stringify(value, null, 2)}</code>
                                                            </pre>
                                                        </div>
                                                    ))}
                                                </AccordionContent>
                                            </AccordionItem>
                                        </Accordion>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}
                </main>
            </div>
        </div>
    );
}
