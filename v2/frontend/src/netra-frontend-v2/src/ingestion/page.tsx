'use client';

import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Zap, Settings, RefreshCw, BarChart2, DollarSign, HelpCircle, LogOut } from 'lucide-react';

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
    params: any;
    result_path?: string;
    summary?: any;
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
    async post(endpoint: string, body: any, token: string | null, expectStatus: number = 202) {
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

export default function IngestionPage() {
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
        } catch (err: any) {
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

    const handleStartIngestion = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);

        const formData = new FormData(event.currentTarget);
        const data_path = formData.get('data_path') as string;
        const table_name = formData.get('table_name') as string;

        try {
            const newJob = await apiService.post(`${config.api.baseUrl}/generation/ingest_data`, { data_path, table_name }, token);
            setJob(newJob);
            setIsPolling(true);
        } catch (err: any) {
            console.error("Error starting ingestion:", err);
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
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1">
                            <Card>
                                <h2 className="text-xl font-semibold text-gray-900">Ingest Data</h2>
                                <p className="mt-1 text-sm text-gray-500">Ingest data from a JSON file into ClickHouse.</p>
                                <form onSubmit={handleStartIngestion} className="mt-6 space-y-4">
                                    <div>
                                        <label htmlFor="data_path" className="block text-sm font-medium text-gray-700">Data Path</label>
                                        <div className="mt-1">
                                            <Input id="data_path" name="data_path" type="text" required defaultValue="generated_logs_v2.json" />
                                        </div>
                                    </div>
                                    <div>
                                        <label htmlFor="table_name" className="block text-sm font-medium text-gray-700">Table Name</label>
                                        <div className="mt-1">
                                            <Input id="table_name" name="table_name" type="text" required defaultValue="netra_logs" />
                                        </div>
                                    </div>
                                    <Button type="submit" isLoading={isLoading || isPolling} disabled={isLoading || isPolling} icon={Zap}>
                                        {isPolling ? 'Ingestion in Progress...' : 'Start Ingestion'}
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
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Ingestion Job</h3>
                <p className="mt-1 text-sm text-gray-500">Start a new ingestion job to see the status here.</p>
            </Card>
        );
    }

    if (job.status === 'pending' || job.status === 'running') {
        return (
            <Card className="h-full">
                <h2 className="text-xl font-semibold text-gray-900">Ingestion in Progress</h2>
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
                <h2 className="text-xl font-semibold text-red-800">Ingestion Failed</h2>
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
                <h2 className="text-2xl font-bold text-gray-900">Ingestion Complete</h2>
                <p className="mt-1 text-sm text-gray-500">Job ID: {job.job_id}</p>
                <div className="mt-6">
                    <p className="text-sm font-medium text-gray-700">Summary:</p>
                    <p className="text-lg font-bold text-gray-800">{job.summary?.message}</p>
                </div>
            </Card>
        );
    }

    return null;
}
