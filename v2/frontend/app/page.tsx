'use client';

import React from 'react';
import { ApexOptimizerAgentV2 } from './components/apex-optimizer-agent-v2';
import { AgentProvider } from './providers/AgentProvider';

export default function ApexOptimizerAgentPage() {
    return (
        <div className="h-full">
            <AgentProvider>
                <ApexOptimizerAgentV2 />
            </AgentProvider>
        </div>
    );
}