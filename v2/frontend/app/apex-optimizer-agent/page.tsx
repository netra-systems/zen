'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { HelpCircle } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { ErrorDisplay } from '@/components/ErrorDisplay';
import { apiService } from '../api';
import { useAgentStreaming } from '../hooks/useAgentStreaming.tsx';
import { getUserId } from '../lib/user';
import useAppStore from '../store';

export default function ApexOptimizerAgentPage() {
    const { token } = useAppStore();
    const { isLoading, error, messages, artifacts, addMessage, startAgent, setIsLoading, setError } = useAgentStreaming(token);
    const [exampleQueries, setExampleQueries] = useState<string[]>([]);

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
        await startAgent(query);
    }, [addMessage, startAgent]);

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <Header />
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
                    <ErrorDisplay error={error} />
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1">
                        <div className="lg:col-span-2 h-[calc(100vh-10rem)]">
                           <ChatWindow
                                messages={messages}
                                onSendMessage={handleSendMessage}
                                isLoading={isLoading}
                                exampleQueries={exampleQueries}
                            />
                        </div>
                        <div className="lg:col-span-1">
                            <Card className="flex flex-col h-full min-h-[300px]">
                                <CardHeader>
                                    <CardTitle>Artifacts</CardTitle>
                                    <CardDescription>Generated artifacts will appear here.</CardDescription>
                                </CardHeader>
                                <CardContent className="flex-1 overflow-auto">
                                    {artifacts.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center text-center h-full">
                                            <HelpCircle className="w-16 h-16 text-gray-300" />
                                        </div>
                                    ) : (
                                        <pre>{JSON.stringify(artifacts, null, 2)}</pre>
                                    )}
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
