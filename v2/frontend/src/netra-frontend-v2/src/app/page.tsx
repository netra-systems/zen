"use client";

import React, { useState, useEffect, useCallback, FormEvent } from 'react';
import { Zap, Settings, RefreshCw, BarChart2, DollarSign, HelpCircle, LogOut } from 'lucide-react';

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
// A simple wrapper for fetch to handle common cases
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
    async post(endpoint: string, body: any, token: string | null, expectStatus: number = 200) {
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


// --- UI Components ---
const Card = ({ children, className = '' }: { children: React.ReactNode, className?: string }) => <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>{children}</div>;

const Button = ({ children, onClick, type = 'button', disabled, isLoading, variant = 'primary', icon: Icon, className = '' }: {
    children: React.ReactNode;
    onClick?: () => void;
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
    isLoading?: boolean;
    variant?: 'primary' | 'secondary' | 'ghost';
    icon?: React.ElementType;
    className?: string;
}) => {
    const baseClasses = 'w-full inline-flex justify-center items-center px-4 py-2 border text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200';
    const variantClasses = {
        primary: 'border-transparent text-white bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500 disabled:bg-indigo-400 disabled:cursor-not-allowed',
        secondary: 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed',
        ghost: 'border-transparent text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:ring-indigo-500',
    };
    return (
        <button type={type} onClick={onClick} disabled={disabled || isLoading} className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
            {isLoading ? <RefreshCw className="animate-spin -ml-1 mr-3 h-5 w-5" /> : (Icon && <Icon className="-ml-1 mr-3 h-5 w-5" />)}
            {children}
        </button>
    );
};

const Spinner = ({ className = '' }: { className?: string }) => (
    <div className={`flex justify-center items-center h-full ${className}`}>
        <div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
    </div>
);

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>((props, ref) => (
    <input
        ref={ref}
        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        {...props}
    />
));
Input.displayName = 'Input';


// --- Main App State and Logic (using a custom hook for encapsulation) ---
function useAppController() {
    const [isMounted, setIsMounted] = useState(false);
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [authError, setAuthError] = useState<string | null>(null);

    const fetchUser = useCallback(async (currentToken: string) => {
        try {
            const userData = await apiService.get('/users/me', currentToken);
            setUser(userData);
        } catch (error) {
            // Token is likely invalid, log out
            console.error("Failed to fetch user, logging out.", error);
            setToken(null);
            setUser(null);
            if (typeof window !== 'undefined') {
                localStorage.removeItem('authToken');
            }
        }
    }, []);

    useEffect(() => {
        setIsMounted(true);
        const storedToken = localStorage.getItem('authToken');
        if (storedToken) {
            setToken(storedToken);
            fetchUser(storedToken).finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, [fetchUser]);

    const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setAuthError(null);
        const formData = new FormData(event.currentTarget);
        
        try {
            const response = await fetch('/auth/token', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                 const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const { access_token } = await response.json();
            localStorage.setItem('authToken', access_token);
            setToken(access_token);
            await fetchUser(access_token);

        } catch (error: any) {
            console.error(error);
            setAuthError(error.message || 'An unexpected error occurred during login.');
        }
    };

    const handleLogout = () => {
        setUser(null);
        setToken(null);
        localStorage.removeItem('authToken');
    };

    return { isMounted, isLoading, user, authError, handleLogin, handleLogout, token };
}


// --- Root Component ---
export default function Home() {
    const { isMounted, isLoading, user, authError, handleLogin, handleLogout, token } = useAppController();

    if (!isMounted || isLoading) {
        return <div className="min-h-screen bg-gray-50"><Spinner className="py-20" /></div>;
    }

    return user && token ? (
        <Dashboard user={user} onLogout={handleLogout} token={token} />
    ) : (
        <LoginPage onLogin={handleLogin} error={authError} />
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
            const data: AnalysisRun = await apiService.get(`/runs/${runId}`, token);
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
            const run = await apiService.post('/runs', { source_table: 'logs' }, token, 202);
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
