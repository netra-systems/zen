'use client';

import React, { useState, useEffect, useCallback, FormEvent, useRef } from 'react';
import { Zap, HelpCircle } from 'lucide-react';

import { config } from '../config';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { GenericInput } from '@/components/GenericInput';
import useAppStore from '../store';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/card';
import Spinner from '@/components/Spinner';
import { Button } from '@/components/button';

// --- Type Definitions for API data ---
interface AgentRun {
    run_id: string;
    status: 'in_progress' | 'awaiting_confirmation' | 'complete' | 'failed';
    current_step: number;
    total_steps: number;
    last_step_result?: any;
    final_report?: string;
    error?: string;
}

interface AgentHistory {
    run_id: string;
    is_complete: boolean;
    history: any;
}

// --- API Service ---
const apiService = {
    async get(endpoint: string, token: string | null) {
        const response = await fetch(endpoint, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
            throw new Error(errorData.detail);
        }
        return response.json();
    },
    async post(endpoint: string, body: Record<string, unknown>, token: string | null, expectStatus: number = 202) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body),
        });
        if (response.status !== expectStatus) {
            const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred.' }));
            throw new Error(errorData.detail);
        }
        return response.json();
    }
};

const exampleQueries = [
    "Analyze the current state of the S&P 500 and provide a summary of its recent performance.",
    "What are the latest trends in the technology sector, and which stocks are leading the way?",
    "Provide a detailed analysis of the real estate market in California, including key metrics and forecasts.",
    "Compare the financial performance of Apple and Microsoft over the last five years.",
    "What is the outlook for the energy sector, considering recent geopolitical events?",
    "Analyze the impact of inflation on consumer spending and the retail industry.",
    "What are the most promising emerging markets for investment right now?"
];

export default function DeepAgentPage() {
    const { token } = useAppStore();
    const [agentRun, setAgentRun] = useState<AgentRun | null>(null);
    const [agentHistory, setAgentHistory] = useState<AgentHistory | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const pollingRunIdRef = useRef<string | null>(null);
    const [query, setQuery] = useState(exampleQueries[Math.floor(Math.random() * exampleQueries.length)]);

    const pollStatus = useCallback(async () => {
        if (!pollingRunIdRef.current) {
            setIsPolling(false);
            return;
        }
        try {
            const data: AgentRun = await apiService.get(`${config.api.baseUrl}/agent/${pollingRunIdRef.current}/step`, token);
            setAgentRun(data);
            if (data.status === 'complete' || data.status === 'failed') {
                setIsPolling(false);
                pollingRunIdRef.current = null;
                const historyData: AgentHistory = await apiService.get(`${config.api.baseUrl}/agent/${data.run_id}/history`, token);
                setAgentHistory(historyData);
            }
        } catch (err: unknown) {
            console.error("Polling failed:", err);
            setError('Could not get agent run status.');
            setIsPolling(false);
            pollingRunIdRef.current = null;
        }
    }, [token, setIsPolling, setAgentRun, setAgentHistory, setError]);

    useEffect(() => {
        if (!isPolling) {
            return;
        }
        const intervalId = setInterval(pollStatus, 3000);
        return () => clearInterval(intervalId);
    }, [isPolling, pollStatus]);

    const handleStartAnalysis = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);
        setAgentRun(null);
        setAgentHistory(null);
        if (isPolling) {
            setIsPolling(false);
        }
        pollingRunIdRef.current = null;

        const formData = new FormData(event.currentTarget);
        const currentQuery = formData.get('query') as string;
        setQuery(currentQuery);
        const run_id = `run-${Date.now()}`;

        try {
            const newRun = await apiService.post(`${config.api.baseUrl}/agent/create`, { run_id, query: currentQuery, data_source: { source_table: 'synthetic_data' }, time_range: { start_time: '2025-01-01T00:00:00Z', end_time: '2025-12-31T23:59:59Z' } }, token);
            if (newRun && newRun.run_id) {
                setAgentRun({ ...newRun, status: 'in_progress', current_step: 0, total_steps: 5 }); // Assuming 5 steps for now
                pollingRunIdRef.current = newRun.run_id;
                setIsPolling(true);
            } else {
                setError("Failed to start analysis: No run ID returned.");
            }
        } catch (err: unknown) {
            console.error("Error starting analysis:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleClear = () => {
        setQuery('');
    }

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <Header />
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
                    {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative mb-6" role="alert">{error}</div>}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1">
                            <GenericInput
                                title="Deep Agent Analysis"
                                description="Start a new deep agent analysis run."
                                inputFields={[
                                    { id: 'query', name: 'query', label: 'Your Query', type: 'textarea', required: true, defaultValue: query },
                                ]}
                                onSubmit={handleStartAnalysis}
                                isLoading={isLoading || isPolling}
                                submitButtonText={isPolling ? 'Analysis in Progress...' : 'Start Analysis'}
                                onClear={handleClear}
                            />
                        </div>
                        <div className="lg:col-span-2">
                            <AgentStatusView agentRun={agentRun} />
                            {agentHistory && <AgentHistoryView agentHistory={agentHistory} />}
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}

const AgentStatusView = ({ agentRun }: { agentRun: AgentRun | null }) => {
    if (!agentRun) {
        return (
            <Card className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <CardHeader>
                    <CardTitle>No Analysis Run</CardTitle>
                    <CardDescription>Start a new analysis to see the status here.</CardDescription>
                </CardHeader>
                <CardContent>
                    <HelpCircle className="w-16 h-16 text-gray-300" />
                </CardContent>
            </Card>
        );
    }

    if (agentRun.status === 'in_progress' || agentRun.status === 'awaiting_confirmation') {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Analysis in Progress</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="mt-4 space-y-2 text-sm text-gray-600">
                        <p><strong>Status:</strong> <span className="capitalize font-medium text-indigo-600">{agentRun.status.toLowerCase()}</span></p>
                        <p><strong>Run ID:</strong> {agentRun.run_id}</p>
                        <p><strong>Step:</strong> {agentRun.current_step} of {agentRun.total_steps}</p>
                    </div>
                    <div className="mt-6">
                        <Spinner />
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (agentRun.status === 'failed') {
        return (
            <Card className="h-full bg-red-50 border-red-200 border">
                <CardHeader>
                    <CardTitle>Analysis Failed</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="mt-4 space-y-2 text-sm text-red-700">
                        <p><strong>Run ID:</strong> {agentRun.run_id}</p>
                    </div>
                    <div className="mt-6">
                        <h3 className="text-sm font-medium text-red-800 mb-2">Error Log</h3>
                        <pre className="bg-red-100 text-red-900 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                            <code>{agentRun.error || "No detailed error log available."}</code>
                        </pre>
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (agentRun.status === 'complete') {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Analysis Complete</CardTitle>
                    <CardDescription>Run ID: {agentRun.run_id}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="mt-6">
                        <p className="text-sm font-medium text-gray-700">Final Report:</p>
                        <p className="text-lg font-bold text-gray-800">{agentRun.final_report}</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return null;
}

const AgentHistoryView = ({ agentHistory }: { agentHistory: AgentHistory | null }) => {
    if (!agentHistory) {
        return null;
    }

    return (
        <Card className="mt-8">
            <CardHeader>
                <CardTitle>Analysis History</CardTitle>
                <CardDescription>Run ID: {agentHistory.run_id}</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {agentHistory.history.messages.map((message: any, index: number) => (
                        <div key={index} className="p-4 border rounded-md">
                            <p className="font-bold">{message.role}</p>
                            <pre className="whitespace-pre-wrap">{JSON.stringify(message.content, null, 2)}</pre>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}