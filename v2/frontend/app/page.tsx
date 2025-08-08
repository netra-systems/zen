'use client';

import React from 'react';
import { ApexOptimizerAgentV2 } from './components/apex-optimizer-agent-v2';
import { AgentProvider } from './providers/AgentProvider';
import { useAuth } from '@/hooks/useAuth';

export default function ApexOptimizerAgentPage() {
    const { user, login, logout, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    return (
        <div className="h-full">
            {user ? (
                <div>
                    <p>Welcome, {user.full_name || user.email}</p>
                    <button onClick={logout}>Logout</button>
                    <AgentProvider>
                        <ApexOptimizerAgentV2 />
                    </AgentProvider>
                </div>
            ) : (
                <button onClick={login}>Login with Google</button>
            )}
        </div>
    );
}