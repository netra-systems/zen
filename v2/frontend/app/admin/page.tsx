'use client';

import React, { useState, useEffect, useCallback, FormEvent, useRef } from 'react';
import { HelpCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

import { config } from '@/config';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { GenericInput } from '@/components/GenericInput';
import useAppStore from '@/store';
import Spinner from '@/components/Spinner';

// --- Type Definitions for API data ---
interface Job {
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    type: string;
    params: Record<string, unknown>;
    result_path?: string;
    summary?: { message: string };
    error?: string;
    last_updated?: number;
    progress?: number;
    total_tasks?: number;
    records_ingested?: number;
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

export default function AdminPage() {
    const { token } = useAppStore();
    const [job, setJob] = useState<Job | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const pollingJobIdRef = useRef<string | null>(null);

    const pollStatus = useCallback(async () => {
        if (!pollingJobIdRef.current) {
            setIsPolling(false); // Stop polling if job id is missing
            return;
        }
        try {
            const data: Job = await apiService.get(`${config.api.baseUrl}/generation/jobs/${pollingJobIdRef.current}`, token);
            setJob(data);
            if (data.status !== 'running' && data.status !== 'pending') {
                setIsPolling(false);
                pollingJobIdRef.current = null;
            }
        } catch (err: unknown) {
            console.error("Polling failed:", err);
            setError('Could not get job status.');
            setIsPolling(false);
            pollingJobIdRef.current = null;
        }
    }, [token, setIsPolling, setJob, setError]);

    useEffect(() => {
        if (!isPolling) {
            return;
        }
        const intervalId = setInterval(pollStatus, 3000);
        return () => clearInterval(intervalId);
    }, [isPolling, pollStatus]);

    const handleStartGeneration = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);
        setJob(null);
        if (isPolling) {
            setIsPolling(false);
        }
        pollingJobIdRef.current = null;


        const formData = new FormData(event.currentTarget);
        const samples_per_type = parseInt(formData.get('samples_per_type') as string, 10);
        const temperature = parseFloat(formData.get('temperature') as string);
        const max_cores = parseInt(formData.get('max_cores') as string, 10);
        const clickhouse_table = formData.get('clickhouse_table') as string;

        try {
            const newJob = await apiService.post(`${config.api.baseUrl}/generation/content_corpus`, { samples_per_type, temperature, max_cores, clickhouse_table }, token);
            if (newJob && newJob.job_id) {
                setJob(newJob);
                pollingJobIdRef.current = newJob.job_id;
                setIsPolling(true);
            } else {
                setError("Failed to start generation job: No job ID returned.");
            }
        } catch (err: unknown) {
            console.error("Error starting generation:", err);
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
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1">
                            <GenericInput
                                title="Generate Content Corpus"
                                description="Generate a new content corpus and store it in ClickHouse."
                                inputFields={[
                                    { id: 'samples_per_type', name: 'samples_per_type', label: 'Samples Per Type', type: 'number', required: true, defaultValue: 10 },
                                    { id: 'temperature', name: 'temperature', label: 'Temperature', type: 'number', required: true, defaultValue: 0.7 },
                                    { id: 'max_cores', name: 'max_cores', label: 'Max Cores', type: 'number', required: true, defaultValue: 4 },
                                    { id: 'clickhouse_table', name: 'clickhouse_table', label: 'ClickHouse Table', type: 'text', required: true, defaultValue: 'content_corpus' },
                                ]}
                                onSubmit={handleStartGeneration}
                                isLoading={isLoading || isPolling}
                                submitButtonText={isPolling ? 'Generation in Progress...' : 'Start Generation'}
                            />
                        </div>
                        <div className="lg:col-span-2">
                            <JobStatusView job={job} />
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}

const JobStatusView = ({ job }: { job: Job | null }) => {
    if (!job) {
        return (
            <Card className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <CardHeader>
                    <CardTitle>No Generation Job</CardTitle>
                    <CardDescription>Start a new generation job to see the status here.</CardDescription>
                </CardHeader>
                <CardContent>
                    <HelpCircle className="w-16 h-16 text-gray-300" />
                </CardContent>
            </Card>
        );
    }

    const progressPercentage = job.total_tasks ? (job.progress / job.total_tasks) * 100 : 0;

    if (job.status === 'pending' || job.status === 'running') {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle>Generation in Progress</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="mt-4 space-y-2 text-sm text-gray-600">
                        <p><strong>Status:</strong> <span className="capitalize font-medium text-indigo-600">{job.status.toLowerCase()}</span></p>
                        <p><strong>Job ID:</strong> {job.job_id}</p>
                        {job.last_updated && <p><strong>Last Updated:</strong> {new Date(job.last_updated * 1000).toLocaleString()}</p>}
                    </div>
                    <div className="mt-6">
                        <Spinner />
                        {job.progress !== undefined && job.total_tasks !== undefined && (
                            <div className="mt-4">
                                <div className="flex justify-between mb-1">
                                    <span className="text-sm font-medium text-gray-700">Generation Progress</span>
                                    <span className="text-sm font-medium text-gray-700">{job.progress} of {job.total_tasks} tasks</span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2.5">
                                    <div className="bg-indigo-600 h-2.5 rounded-full" style={{ width: `${progressPercentage}%` }}></div>
                                </div>
                            </div>
                        )}
                        {job.records_ingested !== undefined && (
                            <div className="mt-4">
                                <p className="text-sm text-gray-600"><strong>Records Ingested:</strong> {job.records_ingested}</p>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (job.status === 'failed') {
        return (
            <Card className="h-full bg-red-50 border-red-200 border">
                <CardHeader>
                    <CardTitle>Generation Failed</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="mt-4 space-y-2 text-sm text-red-700">
                        <p><strong>Job ID:</strong> {job.job_id}</p>
                    </div>
                    <div className="mt-6">
                        <h3 className="text-sm font-medium text-red-800 mb-2">Error Log</h3>
                        <pre className="bg-red-100 text-red-900 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                            <code>{job.error || "No detailed error log available."}</code>
                        </pre>
                    </div>
                </CardContent>
            </Card>
        )
    }

    if (job.status === 'completed') {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Generation Complete</CardTitle>
                    <CardDescription>Job ID: {job.job_id}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="mt-6">
                        <p className="text-sm font-medium text-gray-700">Summary:</p>
                        <p className="text-lg font-bold text-gray-800">{job.summary?.message}</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return null;
}