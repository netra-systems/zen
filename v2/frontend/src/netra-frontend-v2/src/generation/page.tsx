'use client';

import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Zap, HelpCircle } from 'lucide-react';

import { config } from '../config';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import Input from '../components/Input';
import { useAppStore } from '../store';

// --- Type Definitions for API data ---
interface Job {
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    type: string;
    params: Record<string, unknown>;
    result_path?: string;
    summary?: { logs_generated: number };
    error?: string;
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

export default function GenerationPage() {
    const { token } = useAppStore();
    const [job, setJob] = useState<Job | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const pollStatus = useCallback(async (jobId: string) => {
        try {
            const data: Job = await apiService.get(`${config.api.baseUrl}/generation/jobs/${jobId}`, token);
            setJob(data);
            if (data.status !== 'running' && data.status !== 'pending') {
                setIsPolling(false);
            }
        } catch (err: unknown) {
            console.error("Polling failed:", err);
            setError('Could not get job status.');
            setIsPolling(false);
        }
    }, [token]);

    useEffect(() => {
        let intervalId: NodeJS.Timeout | null = null;
        if (isPolling && job?.job_id) {
            intervalId = setInterval(() => pollStatus(job.job_id), 3000);
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [isPolling, job, pollStatus]);

    const handleStartGeneration = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);

        const formData = new FormData(event.currentTarget);
        const num_traces = parseInt(formData.get('num_traces') as string, 10);
        const output_file = formData.get('output_file') as string;

        try {
            const newJob = await apiService.post(`${config.api.baseUrl}/generation/synthetic_data`, { num_traces, output_file }, token);
            setJob(newJob);
            setIsPolling(true);
        } catch (err: unknown) {
            console.error("Error starting generation:", err);
            setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
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
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1">
                            <Card>
                                <h2 className="text-xl font-semibold text-gray-900">Generate Synthetic Data</h2>
                                <p className="mt-1 text-sm text-gray-500">Generate synthetic data for your workload settings.</p>
                                <form onSubmit={handleStartGeneration} className="mt-6 space-y-4">
                                    <div>
                                        <label htmlFor="num_traces" className="block text-sm font-medium text-gray-700">Number of Traces</label>
                                        <div className="mt-1">
                                            <Input id="num_traces" name="num_traces" type="number" required defaultValue="10000" />
                                        </div>
                                    </div>
                                    <div>
                                        <label htmlFor="output_file" className="block text-sm font-medium text-gray-700">Output File Name</label>
                                        <div className="mt-1">
                                            <Input id="output_file" name="output_file" type="text" required defaultValue="generated_logs_v2.json" />
                                        </div>
                                    </div>
                                    <Button type="submit" isLoading={isLoading || isPolling} disabled={isLoading || isPolling} icon={Zap}>
                                        {isPolling ? 'Generation in Progress...' : 'Start Generation'}
                                    </Button>
                                </form>
                            </Card>
                        </div>
                        <div className="lg:col-span-2">
                            <JobStatusView job={job} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

const JobStatusView = ({ job }: { job: Job | null }) => {
    if (!job) {
        return (
            <Card className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <HelpCircle className="w-16 h-16 text-gray-300" />
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Generation Job</h3>
                <p className="mt-1 text-sm text-gray-500">Start a new generation job to see the status here.</p>
            </Card>
        );
    }

    if (job.status === 'pending' || job.status === 'running') {
        return (
            <Card className="h-full">
                <h2 className="text-xl font-semibold text-gray-900">Generation in Progress</h2>
                <div className="mt-4 space-y-2 text-sm text-gray-600">
                    <p><strong>Status:</strong> <span className="capitalize font-medium text-indigo-600">{job.status.toLowerCase()}</span></p>
                    <p><strong>Job ID:</strong> {job.job_id}</p>
                </div>
                <div className="mt-6">
                    <Spinner />
                </div>
            </Card>
        )
    }

    if (job.status === 'failed') {
        return (
            <Card className="h-full bg-red-50 border-red-200 border">
                <h2 className="text-xl font-semibold text-red-800">Generation Failed</h2>
                <div className="mt-4 space-y-2 text-sm text-red-700">
                    <p><strong>Job ID:</strong> {job.job_id}</p>
                </div>
                <div className="mt-6">
                    <h3 className="text-sm font-medium text-red-800 mb-2">Error Log</h3>
                    <pre className="bg-red-100 text-red-900 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                        <code>{job.error || "No detailed error log available."}</code>
                    </pre>
                </div>
            </Card>
        )
    }

    if (job.status === 'completed') {
        return (
            <Card>
                <h2 className="text-2xl font-bold text-gray-900">Generation Complete</h2>
                <p className="mt-1 text-sm text-gray-500">Job ID: {job.job_id}</p>
                <div className="mt-6">
                    <p className="text-sm font-medium text-gray-700">Result Path:</p>
                    <p className="text-lg font-bold text-gray-800">{job.result_path}</p>
                </div>
                <div className="mt-4">
                    <p className="text-sm font-medium text-gray-700">Summary:</p>
                    <p className="text-lg font-bold text-gray-800">{job.summary?.logs_generated.toLocaleString()} logs generated</p>
                </div>
            </Card>
        );
    }

    return null;
}
