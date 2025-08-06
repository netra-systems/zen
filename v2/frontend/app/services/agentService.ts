import { AnalysisRequest } from '@/app/types';
import { config } from '../config';

export interface WebSocketMessage {
    // Define the structure of your WebSocket messages here
    [key: string]: unknown;
}

export const startAgent = async (analysisRequest: AnalysisRequest, clientId: string) => {
    const response = await fetch(`${config.api.baseUrl}/agent/start_agent/${clientId}`, {
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

export const connectToWebSocket = (runId: string, onMessage: (message: WebSocketMessage) => void) => {
    const ws = new WebSocket(`${config.api.wsBaseUrl}/agent/ws/${runId}`);

    ws.onmessage = (event) => {
        onMessage(JSON.parse(event.data));
    };

    return ws;
};