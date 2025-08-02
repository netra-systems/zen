
import { config } from './config';

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
export const apiService = {
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
