"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Zap, Settings, RefreshCw, BarChart2, DollarSign, Clock, HelpCircle } from 'lucide-react';

// --- UI Components ---
const Card = ({ children, className = '' }: { children: React.ReactNode, className?: string }) => <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>{children}</div>;

const Button = ({ children, onClick, disabled, isLoading, variant = 'primary', icon: Icon, className = '' }: {
    children: React.ReactNode;
    onClick: () => void;
    disabled?: boolean;
    isLoading?: boolean;
    variant?: 'primary' | 'secondary';
    icon?: React.ElementType;
    className?: string;
}) => {
    const baseClasses = 'w-full inline-flex justify-center items-center px-4 py-2 border text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2';
    const variantClasses = {
        primary: 'border-transparent text-white bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500 disabled:bg-indigo-400',
        secondary: 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-indigo-500 disabled:bg-gray-100',
    };
    return (
        <button onClick={onClick} disabled={disabled || isLoading} className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
            {isLoading ? <RefreshCw className="animate-spin -ml-1 mr-3 h-5 w-5" /> : (Icon && <Icon className="-ml-1 mr-3 h-5 w-5" />)}
            {children}
        </button>
    );
};

const Spinner = () => <div className="flex justify-center items-center h-full"><div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div></div>;

// --- Main App Component ---
export default function Home() {
    const [user, setUser] = useState<{ full_name?: string; email: string } | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = useCallback(async () => {
        try {
            // This is a placeholder. Replace with your actual API endpoint.
            const response = await fetch('/api/v2/me').catch(() => null);
             if (response && response.ok) {
                setUser(await response.json());
            } else {
                 // For demonstration, let's set a mock user if the API fails
                setUser({ email: 'demo@example.com', full_name: 'Demo User' });
            }
        } catch (error) {
            console.error("Failed to fetch user:", error);
            setUser({ email: 'demo@example.com', full_name: 'Demo User' }); // Fallback for demo
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    if (loading) {
        return <div className="min-h-screen bg-gray-50 flex items-center justify-center"><Spinner /></div>;
    }

    return user ? <Dashboard user={user} onLogout={() => setUser(null)} /> : <LoginPage />;
}

// --- Pages & Views ---
const LoginPage = () => (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center">
        <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900">Netra</h1>
            <p className="mt-2 text-lg text-gray-600">AI-Powered Workload Optimization</p>
        </div>
        <div className="mt-8">
            <Button onClick={() => window.location.href = '/login/google'} variant="secondary">
                Sign in with Google
            </Button>
        </div>
    </div>
);

const Dashboard = ({ user, onLogout }: { user: { full_name?: string; email: string }; onLogout: () => void; }) => {
    const [analysisRun, setAnalysisRun] = useState<any>(null);
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const pollStatus = useCallback(async (runId: string) => {
        try {
            const response = await fetch(`/api/v2/analysis/status/${runId}`);
            if (!response.ok) throw new Error('Failed to fetch status');
            const data = await response.json();
            setAnalysisRun(data);
            if (data.status !== 'running' && data.status !== 'pending') {
                setIsPolling(false);
            }
        } catch (error) {
            console.error("Polling failed:", error);
            setIsPolling(false);
        }
    }, []);

    useEffect(() => {
        let intervalId: NodeJS.Timeout;
        if (isPolling && analysisRun?.id) {
            intervalId = setInterval(() => pollStatus(analysisRun.id), 2000);
        }
        return () => clearInterval(intervalId);
    }, [isPolling, analysisRun, pollStatus]);
    
    const handleStartAnalysis = async () => {
        setIsLoading(true);
        try {
            const response = await fetch('/api/v2/analysis/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: { source_type: 'synthetic_data' } }),
            });
            if (response.ok) {
                const run = await response.json();
                setAnalysisRun(run);
                setIsPolling(true);
            } else {
                console.error("Failed to start analysis");
            }
        } catch (error) {
            console.error("Error starting analysis:", error);
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
                            <a href="/logout" onClick={(e) => { e.preventDefault(); onLogout(); }} className="text-sm font-medium text-gray-500 hover:text-gray-700">Logout</a>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="py-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-1">
                            <Card>
                                <h2 className="text-xl font-semibold text-gray-900">Control Panel</h2>
                                <p className="mt-1 text-sm text-gray-500">Start a new analysis or manage settings.</p>
                                <div className="mt-6 space-y-4">
                                    <Button onClick={handleStartAnalysis} isLoading={isLoading || isPolling} disabled={isLoading || isPolling} icon={Zap}>
                                        {isPolling ? 'Analysis in Progress...' : 'Start New Analysis'}
                                    </Button>
                                    <Button onClick={() => alert('Manage settings clicked!')} variant="secondary" icon={Settings}>
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

const AnalysisResultView = ({ analysisRun }: { analysisRun: any }) => {
    if (!analysisRun) {
        return (
            <Card className="flex flex-col items-center justify-center text-center h-full">
                <HelpCircle className="w-16 h-16 text-gray-300"/>
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Analysis Run</h3>
                <p className="mt-1 text-sm text-gray-500">Start a new analysis to see the results here.</p>
            </Card>
        );
    }
    
    if (analysisRun.status === 'pending' || analysisRun.status === 'running') {
        return (
            <Card className="h-full">
                 <h2 className="text-xl font-semibold text-gray-900">Analysis in Progress</h2>
                 <div className="mt-4 space-y-2 text-sm text-gray-600">
                     <p><strong>Status:</strong> <span className="capitalize font-medium text-indigo-600">{analysisRun.status}</span></p>
                     <p><strong>Run ID:</strong> {analysisRun.id}</p>
                 </div>
                 <div className="mt-6">
                    <pre className="bg-gray-800 text-white rounded-md p-4 text-xs max-h-60 overflow-y-auto">
                        <code>{analysisRun.execution_log || "Waiting for logs..."}</code>
                    </pre>
                 </div>
            </Card>
        )
    }
    
    if (analysisRun.status === 'failed') {
        return <Card>Error: Analysis Failed. Check logs.</Card>;
    }

    if (analysisRun.status === 'completed' && analysisRun.result_summary) {
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
                        <p className="text-4xl font-bold text-blue-800">{delta_percent}%</p>
                    </div>
                </div>
                <div className="mt-8">
                     <h3 className="text-lg font-medium text-gray-900">Discovered Patterns & Policies</h3>
                     <p className="mt-2 text-sm text-gray-600">Detailed pattern analysis and routing policies will be displayed here.</p>
                </div>
            </Card>
        );
    }

    return null;
}
