'use client';

import React, { useState, FormEvent } from 'react';
import { Send } from 'lucide-react';

import { config } from '../config';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { GenericInput } from '@/components/GenericInput';
import useAppStore from '../store';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/card';

// --- API Service ---
const apiService = {
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

interface AgentResponse {
    // Define the structure of the agent response here
    // For example:
    data: Record<string, unknown>;
    // Add other properties as needed
}

export default function DemoPage() {
    const { token } = useAppStore();
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState<AgentResponse | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleQuery = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const res = await apiService.post(`${config.api.baseUrl}/generation/demo_agent`, { query }, token);
            setResponse(res);
        } catch (err: unknown) {
            console.error("Error querying agent:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="grid min-h-screen w-full md:grid-cols-[220px_1fr] lg:grid-cols-[280px_1fr]">
            <Sidebar />
            <div className="flex flex-col">
                <Header />
                <main className="flex flex-1 flex-col gap-4 p-4 lg:gap-6 lg:p-6">
                    {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative mb-6" role="alert">{error}</div>}
                    <GenericInput
                        title="Demo Agent"
                        description="Interact with the Netra Deep Agent."
                        inputFields={[
                            { id: 'query', name: 'query', label: 'Query', type: 'text', required: true, defaultValue: '' },
                        ]}
                        onSubmit={handleQuery}
                        isLoading={isLoading}
                        submitButtonText="Send"
                    />

                    {response && (
                        <Card className="mt-8">
                            <CardHeader>
                                <CardTitle>Agent Response</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <pre className="mt-2 bg-gray-100 text-gray-800 rounded-md p-4 text-xs max-h-96 overflow-y-auto font-mono">
                                    <code>{JSON.stringify(response, null, 2)}</code>
                                </pre>
                            </CardContent>
                        </Card>
                    )}
                </main>
            </div>
        </div>
    );
}
