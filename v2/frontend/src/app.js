// /frontend/src/App.js
import React, { useState, useEffect, useCallback } from 'react';

// --- Helper Components (Spinner, Card, Button, Input) ---
// (Content is identical to previous version, omitted for brevity)
const Spinner = () => <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>;
const Card = ({ children, className }) => <div className={`bg-white rounded-lg shadow-md p-6 md:p-8 ${className}`}>{children}</div>;
const Button = ({ children, onClick, disabled, isLoading, className = '' }) => <button onClick={onClick} disabled={disabled || isLoading} className={`w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300 disabled:cursor-not-allowed ${className}`}>{isLoading && <Spinner />}{children}</button>;
const Input = ({ id, label, type, value, onChange, placeholder, required }) => <div><label htmlFor={id} className="block text-sm font-medium text-gray-700">{label}</label><div className="mt-1"><input type={type} name={id} id={id} value={value} onChange={onChange} className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md" placeholder={placeholder} required={required} /></div></div>;

// --- NEW: Supply Management Component ---
const SupplyManagement = () => {
    const [supplyOptions, setSupplyOptions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchSupplyOptions = useCallback(async () => {
        try {
            const response = await fetch('http://localhost:8000/api/supply');
            if (!response.ok) throw new Error('Failed to fetch supply options');
            const data = await response.json();
            setSupplyOptions(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSupplyOptions();
    }, [fetchSupplyOptions]);

    // TODO: Add functions to handle add, edit, delete operations

    return (
        <Card className="col-span-1 md:col-span-2">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Supply Catalog Management</h3>
            <p className="mt-1 text-sm text-gray-500">View and manage available LLM supply options.</p>
            {isLoading && <div className="mt-4">Loading options...</div>}
            {error && <div className="mt-4 text-red-500">{error}</div>}
            {!isLoading && !error && (
                <div className="mt-6 flow-root">
                    <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                        <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                            <table className="min-w-full divide-y divide-gray-300">
                                <thead>
                                    <tr>
                                        <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-0">Model Name</th>
                                        <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Provider</th>
                                        <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Cost (Prompt/Completion)</th>
                                        <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">Quality</th>
                                        <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-0"><span className="sr-only">Edit</span></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {supplyOptions.map((option) => (
                                        <tr key={option.option_id}>
                                            <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm font-medium text-gray-900 sm:pl-0">{option.model.name}</td>
                                            <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{option.model.provider}</td>
                                            <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">${option.cost_per_million_tokens_usd.prompt.toFixed(2)} / ${option.cost_per_million_tokens_usd.completion.toFixed(2)}</td>
                                            <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{option.quality_score}</td>
                                            <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-0">
                                                <a href="#" className="text-indigo-600 hover:text-indigo-900">Edit</a>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </Card>
    );
}


// --- Main Application Components (Dashboard, LoginPage, App) ---
const Dashboard = ({ user }) => {
    // State for credentials and analysis remains the same
    const [credentials, setCredentials] = useState({ host: '', port: 9440, user: '', password: '', database: '' });
    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [analysisRun, setAnalysisRun] = useState(null);
    const [analysisStatus, setAnalysisStatus] = useState(null);
    const [isPolling, setIsPolling] = useState(false);

    // All handler functions (handleInputChange, handleSubmitCredentials, etc.) are identical
    const handleInputChange = (e) => setCredentials(prev => ({ ...prev, [e.target.id]: e.target.value }));
    const handleSubmitCredentials = async (e) => {/* ... */};
    const handleStartAnalysis = async () => {/* ... */};
    const pollStatus = useCallback(async (runId) => {/* ... */}, []);
    useEffect(() => { /* ... */ }, [isPolling, analysisRun, pollStatus]);

    return (
        <div className="min-h-screen bg-gray-100">
            <nav className="bg-white shadow-sm">{/* ... Nav bar is identical ... */}</nav>
            <div className="py-10">
                <header>
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <h1 className="text-3xl font-bold leading-tight text-gray-900">Dashboard</h1>
                    </div>
                </header>
                <main>
                    <div className="max-w-7xl mx-auto sm:px-6 lg:px-8 mt-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Credentials and Analysis Cards are the same */}
                        <Card>{/* ... Credentials Form ... */}</Card>
                        <Card>{/* ... Analysis Runner ... */}</Card>
                        
                        {/* NEW: Add the Supply Management Card to the dashboard */}
                        <SupplyManagement />
                    </div>
                </main>
            </div>
        </div>
    );
};

const LoginPage = () => {/* ... Identical to previous version ... */};

export default function App() {
    // App component logic is identical
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchUser() {
            try {
                const response = await fetch('http://localhost:8000/api/me');
                if (response.ok) setUser(await response.json());
            } catch (error) { console.log("Not logged in"); } 
            finally { setLoading(false); }
        }
        fetchUser();
    }, []);

    if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    return user ? <Dashboard user={user} /> : <LoginPage />;
}
