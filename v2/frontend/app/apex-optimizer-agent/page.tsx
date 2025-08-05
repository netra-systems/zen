'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { HelpCircle } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { ErrorDisplay } from '@/components/ErrorDisplay';
import { AutoLoadSwitch } from '@/components/AutoLoadSwitch';
import { apiService } from '../api';
import { useAgentPolling } from '../hooks/useAgentPolling.tsx';
import { getUserId } from '../lib/user';
import useAppStore from '../store';

export default function ApexOptimizerAgentPage() {
    const { token } = useAppStore();
    const { isPolling, isLoading, error, messages, addMessage, startPolling, setIsLoading, setError } = useAgentPolling(token);
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

    const startAgent = useCallback(async (query: string) => {
        setIsLoading(true);
        setError(null);

        const run_id = `run-${Date.now()}`;
        const user_id = getUserId();

        if (!user_id) {
            const err = new Error("User not found. Please log in again.");
            setError(err);
            addMessage('agent', "User not found. Please log in again.");
            setIsLoading(false);
            return;
        }

        try {
            const newRun = await apiService.startAgent(token, {
                settings: {
                    debug_mode: false,
                },
                request: {
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
                    constraints: null
                }
            });

            if (newRun && newRun.run_id) {
                startPolling(newRun.run_id);
                addMessage('agent', `Starting analysis with Run ID: ${newRun.run_id}`);
            } else {
                const err = new Error("Failed to start analysis: No run ID returned.");
                setError(err);
                addMessage('agent', "Failed to start analysis: No run ID returned.");
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Error starting analysis:", err);
            setError(err as Error);
            addMessage('agent', `Error starting analysis.`);
            setIsLoading(false);
        }
    }, [addMessage, setError, setIsLoading, startPolling, token]);

    const handleSendMessage = useCallback(async (query: string) => {
        addMessage('user', query);
        await startAgent(query);
    }, [addMessage, startAgent]);

    useEffect(() => {
        if (autoLoadExample && exampleQueries.length > 0 && !hasLoadedExample) {
            handleSendMessage(exampleQueries[0]);
            setHasLoadedExample(true);
        }
    }, [autoLoadExample, exampleQueries, hasLoadedExample, handleSendMessage]);

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
