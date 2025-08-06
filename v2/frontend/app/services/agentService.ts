
import { AnalysisRequest } from '@/app/types';
import { API_URL } from '../config';

export const startAgent = async (analysisRequest: AnalysisRequest, clientId: string) => {
    const response = await fetch(`${API_URL}/agent/start_agent/${clientId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(analysisRequest),
    });

    if (!response.ok) {
        throw new Error('Failed to start agent');
    }

    return await response.json();
};

export const connectToWebSocket = (runId: string, onMessage: (message: any) => void) => {
    const ws = new WebSocket(`${API_URL}/agent/${runId}`);

    ws.onmessage = (event) => {
        onMessage(JSON.parse(event.data));
    };

    return ws;
};
