'use client';

import React, { useState, FormEvent } from 'react';
import { Send } from 'lucide-react';

import { config } from '../../src/config';
import Card from '../components/Card';
import Button from '../components/Button';
import Input from '../components/Input';
import { useAppStore } from '../../src/store';

// --- API Service ---
const apiService = {
    async post(endpoint: string, body: any, token: string | null) {
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

export default function DemoPage() {
    const { token } = useAppStore();
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState<any | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleQuery = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const res = await apiService.post(`${config.api.baseUrl}/generation/demo_agent`, { query }, token);
            setResponse(res);
        } catch (err: any) {
            console.error("Error querying agent:", err);
            setError(err.message || 'An unexpected error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <nav className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex items-center">
                            <h1 className="text-2xl font-bold text-indigo-600">Netra</h1>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="py-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative mb-6" role="alert">{error}</div>}
                    <Card>
                        <h2 className="text-xl font-semibold text-gray-900">Demo Agent</h2>
                        <p className="mt-1 text-sm text-gray-500">Interact with the Netra Deep Agent.</p>
                                                        <form onSubmit={handleQuery} className="mt-6">
                            <div className="flex items-center">
                                <Input
                                    id="query"
                                    name="query"
                                    type="text"
                                    required
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Enter your query..."
                                    className="flex-grow"
                                />
                                <Button type="submit" isLoading={isLoading} disabled={isLoading} icon={Send} className="ml-2">
                                    Send
                                </Button>
                            </div>
                            <div className="mt-4">
                                <label className="flex items-center">
                                    <input type="checkbox" name="debug_mode" className="form-checkbox" />
                                    <span className="ml-2 text-sm text-gray-600">Debug Mode</span>
                                </label>
                            </div>
                        </form>
                    </Card>

                    {response && (
                        <Card className="mt-8">
                            <h3 className="text-lg font-medium text-gray-900">Agent Response</h3>
                            <pre className="mt-2 bg-gray-100 text-gray-800 rounded-md p-4 text-xs max-h-96 overflow-y-auto font-mono">
                                <code>{JSON.stringify(response, null, 2)}</code>
                            </pre>
                        </Card>
                    )}
                </div>
            </main>
        </div>
    );
}
