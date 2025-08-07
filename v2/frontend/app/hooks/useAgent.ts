
import { getToken, getUserId } from '../lib/user';
import { useCallback, useEffect, useState } from 'react';
import { Message, StreamEvent } from '../types/chat';
import { produce } from 'immer';
import { useWebSocket, WebSocketStatus } from './useWebSocket';

const processStreamEvent = (draft: Message[], event: StreamEvent) => {
    const { event: eventName, data, run_id } = event;

    let existingMessage = draft.find((m) => m.id === run_id) as Message | undefined;

    if (!existingMessage) {
        const newMessage: Message = {
            id: run_id || `msg_${Date.now()}`,
            role: 'agent',
            timestamp: new Date().toISOString(),
            type: 'artifact',
            name: eventName,
            data: data,
        };
        draft.push(newMessage);
        existingMessage = newMessage;
    } else {
        existingMessage.name = eventName;
        existingMessage.data = data;
    }
};

export function useAgent() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [showThinking, setShowThinking] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [socketUrl, setSocketUrl] = useState<string | null>(null);
    const { sendMessage, lastMessage, status } = useWebSocket(socketUrl);

    useEffect(() => {
        if (status === WebSocketStatus.Open && lastMessage) {
            const message: StreamEvent = JSON.parse(lastMessage.data);
            console.log('Received message:', message);

            if (message.event === 'run_complete') {
                setShowThinking(false);
                return;
            }

            setMessages((draft) => produce(draft, (d) => processStreamEvent(d, message)));
        }
    }, [lastMessage, status]);

    const startAgent = useCallback(
        async (message: string) => {
            const token = await getToken();
            if (!token) {
                setError(new Error('Authentication token not found.'));
                return;
            }

            const runId = `run_${Date.now()}`;
            setSocketUrl(`ws://localhost:8000/agent/${runId}?token=${token}`);

            const userMessage: Message = {
                id: `msg_${Date.now()}`,
                role: 'user',
                timestamp: new Date().toISOString(),
                type: 'text',
                content: message,
            };
            setMessages((prev) => [...prev, userMessage]);

            setShowThinking(true);
            setError(null);

            const userId = getUserId();
            if (!userId) {
                console.error('User ID not found');
                setError(new Error('User ID not found.'));
                setShowThinking(false);
                return;
            }

            const analysisRequest = {
                settings: {
                    debug_mode: false,
                },
                request: {
                    id: runId,
                    user_id: userId,
                    query: message,
                    workloads: [],
                },
            };
            sendMessage({ action: 'start_agent', payload: analysisRequest });
        },
        [sendMessage],
    );

    return { startAgent, messages, showThinking, error };
}
