'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { HelpCircle } from 'lucide-react';

import { config } from '../config';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import useAppStore from '../store';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { ChatMessageProps } from '@/components/chat/ChatMessage';
import { ErrorDisplay } from '@/components/ErrorDisplay';
import { AutoLoadSwitch } from '@/components/AutoLoadSwitch';

// --- Type Definitions for API data ---
interface AgentRun {
    run_id: string;
    status: 'in_progress' | 'awaiting_confirmation' | 'complete' | 'failed';
    current_step: number;
    total_steps: number;
    last_step_result?: any;
    final_report?: string;
    error?: any;
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
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
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
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }
        return response.json();
    }
};

export default function DeepAgentPage() {
    const { token } = useAppStore();
    const [messages, setMessages] = useState<ChatMessageProps['message'][]>([]);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<any | null>(null);
    const pollingRunIdRef = useRef<string | null>(null);
    const [exampleQueries, setExampleQueries] = useState<string[]>([]);
    const [hasLoadedExample, setHasLoadedExample] = useState(false);
    const [autoLoadExample, setAutoLoadExample] = useState(true);

    useEffect(() => {
        const storedValue = localStorage.getItem('autoLoadExample');
        if (storedValue !== null) {
            setAutoLoadExample(JSON.parse(storedValue));
        }
    }, []);

    useEffect(() => {
        async function fetchExamples() {
            try {
                const examples = await apiService.get('/api/examples', token);
                setExampleQueries(examples);
            } catch (error) {
                console.error("Failed to fetch examples:", error);
            }
        }
        fetchExamples();
    }, [token]);

    const handleSendMessage = useCallback(async (query: string) => {
        addMessage('user', query);
        setIsLoading(true);
        setError(null);
        if (isPolling) {
            setIsPolling(false);
        }
        pollingRunIdRef.current = null;

        const run_id = `run-${Date.now()}`;
        let user_id = useAppStore.getState().user?.id;

        if (!user_id && process.env.NODE_ENV === 'development') {
            user_id = 'dev-user'; // Dummy user ID for development
        }

        if (!user_id) {
            const err = { detail: "User not found. Please log in again." };
            setError(err);
            addMessage('agent', "User not found. Please log in again.");
            setIsLoading(false);
            return;
        }

        try {
            const newRun = await apiService.post(
                `${config.api.baseUrl}/agent/create`,
                {
                    user_id,
                    query,
                    workloads: [
                        {
                            run_id,
                            query,
                            data_source: { source_table: 'synthetic_data' },
                            time_range: { start_time: '2025-01-01T00:00:00Z', end_time: '2025-12-31T23:59:59Z' }
                        }
                    ],
                    debug_mode: false,
                    constraints: null,
                    negotiated_discount_percent: 0
                },
                token
            );
            if (newRun && newRun.run_id) {
                pollingRunIdRef.current = newRun.run_id;
                setIsPolling(true);
                addMessage('agent', `Starting analysis with Run ID: ${newRun.run_id}`);
            } else {
                const err = { detail: "Failed to start analysis: No run ID returned." };
                setError(err);
                addMessage('agent', "Failed to start analysis: No run ID returned.");
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Error starting analysis:", err);
            setError(err);
            addMessage('agent', `Error starting analysis.`);
            setIsLoading(false);
        }
    }, [token, isPolling]);

    useEffect(() => {
        if (autoLoadExample && exampleQueries.length > 0 && !hasLoadedExample) {
            handleSendMessage(exampleQueries[0]);
            setHasLoadedExample(true);
        }
    }, [autoLoadExample, exampleQueries, hasLoadedExample, handleSendMessage]);


    const addMessage = (role: 'user' | 'agent', content: React.ReactNode) => {
        setMessages(prev => [...prev, { role, content }]);
    };

    const pollStatus = useCallback(async () => {
        if (!pollingRunIdRef.current) {
            setIsPolling(false);
            return;
        }
        try {
            const data: AgentRun = await apiService.get(`${config.api.baseUrl}/agent/${pollingRunIdRef.current}/step`, token);

            if (data.last_step_result) {
                addMessage('agent', <pre>{JSON.stringify(data.last_step_result, null, 2)}</pre>);
            }

            if (data.status === 'complete' || data.status === 'failed') {
                setIsPolling(false);
                pollingRunIdRef.current = null;
                if (data.status === 'complete') {
                    addMessage('agent', data.final_report || 'Analysis complete.');
                } else {
                    setError(data.error || 'Unknown error');
                    addMessage('agent', `Analysis failed.`);
                }
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Polling failed:", err);
            setError(err);
            addMessage('agent', `Error polling for status.`);
            setIsPolling(false);
            pollingRunIdRef.current = null;
            setIsLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!isPolling) {
            return;
        }
        const intervalId = setInterval(pollStatus, 3000);
        return () => clearInterval(intervalId);
    }, [isPolling, pollStatus]);

    const handleAutoLoadChange = (value: boolean) => {
        localStorage.setItem('autoLoadExample', JSON.stringify(value));
        window.location.reload();
    };

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <Header />
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
                    <div className="flex justify-end">
                        <AutoLoadSwitch isAutoLoad={autoLoadExample} onAutoLoadChange={handleAutoLoadChange} />
                    </div>
                    <ErrorDisplay error={error} />
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1">
                        <div className="lg:col-span-2 h-[calc(100vh-10rem)]">
                           <ChatWindow
                                messages={messages}
                                onSendMessage={handleSendMessage}
                                isLoading={isLoading || isPolling}
                                exampleQueries={exampleQueries}
                            />
                        </div>
                        <div className="lg:col-span-1">
                            <Card className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                                <CardHeader>
                                    <CardTitle>Artifacts</CardTitle>
                                    <CardDescription>Generated artifacts will appear here.</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <HelpCircle className="w-16 h-16 text-gray-300" />
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}