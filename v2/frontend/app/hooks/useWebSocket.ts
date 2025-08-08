import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketStatus } from '@/app/types';
import WebSocketService from '@/app/services/websocket';

const useWebSocket = (url: string) => {
    const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
    const [lastJsonMessage, setLastJsonMessage] = useState<any | null>(null);
    const webSocketService = useRef<WebSocketService | null>(null);

    const handleMessage = useCallback((event: MessageEvent) => {
        try {
            const message = JSON.parse(event.data);
            setLastJsonMessage(message);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }, []);

    useEffect(() => {
        webSocketService.current = new WebSocketService(url);

        webSocketService.current.onStatusChange(setStatus);
        webSocketService.current.onMessage(handleMessage);

        webSocketService.current.connect();

        return () => {
            if (webSocketService.current) {
                webSocketService.current.disconnect();
            }
        };
    }, [url, handleMessage]);

    const sendMessage = (message: any) => {
        if (webSocketService.current) {
            webSocketService.current.sendMessage(message);
        }
    };

    return { status, lastJsonMessage, sendMessage };
};

export default useWebSocket;
