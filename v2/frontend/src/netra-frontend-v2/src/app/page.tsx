"use client";

import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Zap, Settings, RefreshCw, BarChart2, DollarSign, HelpCircle, LogOut } from 'lucide-react';

import { config } from '../config';

// --- Type Definitions for API data ---
interface User {
    full_name?: string;
    email: string;
}

interface AnalysisResultSummary {
    projected_monthly_savings: number;
    delta_percent: number;
}

interface AnalysisRun {
    id: string;
    status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
    execution_log: string;
    result_summary: AnalysisResultSummary | null;
}

// --- API Service ---
import { apiService } from '../api';


import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import Input from '../components/Input';


import { useAppStore } from '../store';

// --- Root Component ---
export default function Home() {
    const {
        isLoading,
        user,
        authError,
        login,
        logout,
        token,
        fetchUser,
    } = useAppStore();

    useEffect(() => {
        const storedToken = localStorage.getItem('authToken');
        if (storedToken) {
            fetchUser(storedToken);
        }
    }, [fetchUser]);

    if (isLoading) {
        return <div className="min-h-screen bg-gray-50"><Spinner className="py-20" /></div>;
    }

    return user && token ? (
        <Dashboard user={user} onLogout={logout} token={token} />
    ) : (
        <LoginPage onLogin={login} error={authError} />
    );
}

// --- Pages & Views ---
const LoginPage = ({ onLogin, error }: { onLogin: (e: FormEvent<HTMLFormElement>) => Promise<void>; error: string | null }) => (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4">
        <div className="text-center">
            <h1 className="text-5xl font-bold text-indigo-600">Netra</h1>
            <p className="mt-3 text-xl text-gray-600">AI-Powered Workload Optimization</p>
        </div>
        <div className="mt-10 max-w-sm w-full">
            <Card>
                <form onSubmit={onLogin} className="space-y-6">
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700">Email address</label>
                        <div className="mt-1">
                            <Input id="username" name="username" type="email" autoComplete="email" required defaultValue="jdoe@example.com" />
                        </div>
                    </div>
                    <div>
                        <label htmlFor="password"className="block text-sm font-medium text-gray-700">Password</label>
                        <div className="mt-1">
                            <Input id="password" name="password" type="password" required defaultValue="secret" />
                        </div>
                    </div>
                    {error && <p className="text-xs text-red-600">{error}</p>}
                    <div>
                        <Button type="submit" variant="primary" className="w-full">
                            Sign In
                        </Button>
                    </div>
                </form>
            </Card>
             <p className="mt-4 text-center text-xs text-gray-500">Use default credentials to sign in.</p>
        </div>
    </div>
);

const Dashboard = ({ user, onLogout, token }: { user: User; onLogout: () => void; token: string }) => {
    const [analysisRun, setAnalysisRun] = useState<AnalysisRun | null>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const pollStatus = useCallback(async (runId: string) => {
        try {
            const data: AnalysisRun = await apiService.get(`${config.api.endpoints.runs}/${runId}`, token);
            setAnalysisRun(data);
            if (data.status !== 'RUNNING' && data.status !== 'PENDING') {
                setIsPolling(false);
            }
        } catch (err: any) {
            console.error("Polling failed:", err);
            setError('Could not get analysis status.');
            setIsPolling(false);
        }
    }, [token]);

    useEffect(() => {
        let intervalId: NodeJS.Timeout | null = null;
        if (isPolling && analysisRun?.id) {
            intervalId = setInterval(() => pollStatus(analysisRun.id), 3000);
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [isPolling, analysisRun, pollStatus]);
    
    const handleStartAnalysis = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const run = await apiService.post(config.api.endpoints.runs, { source_table: 'logs' }, token, 202);
            setAnalysisRun(run);
            setIsPolling(true);
        } catch (err: any) {
            console.error("Error starting analysis:", err);
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
                        <div className="flex items-center">
                            <span className="text-sm text-gray-600 mr-4">Welcome, {user.full_name || user.email}</span>
                            <Button onClick={onLogout} variant="ghost" icon={LogOut}>Logout</Button>
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
                                <h2 className="text-xl font-semibold text-gray-900">Control Panel</h2>
                                <p className="mt-1 text-sm text-gray-500">Start a new analysis or manage settings.</p>
                                <div className="mt-6 space-y-4">
                                    <Button onClick={handleStartAnalysis} isLoading={isLoading || isPolling} disabled={isLoading || isPolling} icon={Zap}>
                                        {isPolling ? 'Analysis in Progress...' : 'Start New Analysis'}
                                    </Button>
                                    <Button onClick={() => window.location.href = '/admin'} variant="secondary" icon={Settings} disabled={isLoading || isPolling}>
                                        Admin Panel
                                    </Button>
                                    <Button onClick={() => window.location.href = '/generation'} variant="secondary" icon={Settings} disabled={isLoading || isPolling}>
                                        Generate Synthetic Data
                                    </Button>
                                    <Button onClick={() => window.location.href = '/ingestion'} variant="secondary" icon={Settings} disabled={isLoading || isPolling}>
                                        Ingest Data
                                    </Button>
                                    <Button onClick={() => window.location.href = '/demo'} variant="secondary" icon={Settings} disabled={isLoading || isPolling}>
                                        Demo Agent
                                    </Button>
                                    <Button onClick={() => alert('This feature is not yet implemented.')} variant="secondary" icon={Settings} disabled={isLoading || isPolling}>
                                        Manage Supply Catalog
                                    </Button>
                                </div>
                            </Card>
                        </div>
                        <div className="lg:col-span-2">
                             <AnalysisResultView analysisRun={analysisRun} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

const AnalysisResultView = ({ analysisRun }: { analysisRun: AnalysisRun | null }) => {
    if (!analysisRun) {
        return (
            <Card className="flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <HelpCircle className="w-16 h-16 text-gray-300"/>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Analysis Run</h3>
                <p className="mt-1 text-sm text-gray-500">Start a new analysis to see the results here.</p>
            </Card>
        );
    }
    
    if (analysisRun.status === 'PENDING' || analysisRun.status === 'RUNNING') {
        return (
            <Card className="h-full">
                 <h2 className="text-xl font-semibold text-gray-900">Analysis in Progress</h2>
                 <div className="mt-4 space-y-2 text-sm text-gray-600">
                     <p><strong>Status:</strong> <span className="capitalize font-medium text-indigo-600">{analysisRun.status.toLowerCase()}</span></p>
                     <p><strong>Run ID:</strong> {analysisRun.id}</p>
                 </div>
                 <div className="mt-6">
                    <h3 className="text-sm font-medium text-gray-800 mb-2">Execution Log</h3>
                    <pre className="bg-gray-800 text-white rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                        <code>{analysisRun.execution_log || "Waiting for logs..."}</code>
                    </pre>
                 </div>
            </Card>
        )
    }
    
    if (analysisRun.status === 'FAILED') {
        return (
            <Card className="h-full bg-red-50 border-red-200 border">
                 <h2 className="text-xl font-semibold text-red-800">Analysis Failed</h2>
                 <div className="mt-4 space-y-2 text-sm text-red-700">
                     <p><strong>Run ID:</strong> {analysisRun.id}</p>
                 </div>
                 <div className="mt-6">
                    <h3 className="text-sm font-medium text-red-800 mb-2">Error Log</h3>
                    <pre className="bg-red-100 text-red-900 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                        <code>{analysisRun.execution_log || "No detailed error log available."}</code>
                    </pre>
                 </div>
            </Card>
        )
    }

    if (analysisRun.status === 'COMPLETED' && analysisRun.result_summary) {
         const { projected_monthly_savings, delta_percent } = analysisRun.result_summary;
        return (
            <Card>
                <h2 className="text-2xl font-bold text-gray-900">Analysis Complete</h2>
                <p className="mt-1 text-sm text-gray-500">Run ID: {analysisRun.id}</p>
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6 text-center">
                    <div className="bg-green-50 p-6 rounded-lg">
                        <DollarSign className="w-12 h-12 text-green-600 mx-auto"/>
                        <p className="mt-4 text-sm font-medium text-green-700">Projected Monthly Savings</p>
                        <p className="text-4xl font-bold text-green-800">${projected_monthly_savings.toLocaleString()}</p>
                    </div>
                     <div className="bg-blue-50 p-6 rounded-lg">
                        <BarChart2 className="w-12 h-12 text-blue-600 mx-auto"/>
                        <p className="mt-4 text-sm font-medium text-blue-700">Cost Reduction</p>
                        <p className="text-4xl font-bold text-blue-800">{delta_percent.toFixed(2)}%</p>
                    </div>
                </div>
                <div className="mt-8">
                     <h3 className="text-lg font-medium text-gray-900">Execution Log</h3>
                      <pre className="mt-2 bg-gray-100 text-gray-800 rounded-md p-4 text-xs max-h-60 overflow-y-auto font-mono">
                        <code>{analysisRun.execution_log}</code>
                    </pre>
                </div>
            </Card>
        );
    }

    return null;
}
