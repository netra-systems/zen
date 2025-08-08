import { useEffect, useRef, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { ChatMessage } from '@/types';

const WS_URL = 'ws://localhost:8000/ws';

export const useWebSocket = (runId: string) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const webSocketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        if (!runId) return;

        const connect = () => {
            const ws = new WebSocket(`${WS_URL}/${runId}`);
            webSocketRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket connected');
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data) as ChatMessage;
                if (message.event === 'chat_message') {
                    setMessages((prevMessages) => [...prevMessages, message]);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                setIsConnected(false);
                // Attempt to reconnect after a delay
                setTimeout(connect, 5000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                ws.close();
            };
        };

        connect();

        return () => {
            if (webSocketRef.current) {
                webSocketRef.current.close();
            }
        };
    }, [runId]);

    const sendMessage = (message: any) => {
        if (webSocketRef.current && webSocketRef.current.readyState === WebSocket.OPEN) {
            webSocketRef.current.send(JSON.stringify(message));
        }
    };

    return { messages, sendMessage, isConnected };
}; 
