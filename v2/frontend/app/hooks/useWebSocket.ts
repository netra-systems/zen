
import { useState, useEffect, useCallback } from 'react';
import { WebSocketStatus } from '@/app/types';
import webSocketService from '@/services/websocket';

const useWebSocket = () => {
    const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
    const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);

    useEffect(() => {
        const handleMessage = (message: any) => {
            setLastJsonMessage(message);
        };

        webSocketService.onStatusChange(setStatus);
        webSocketService.onMessage(handleMessage);

        return () => {
            // Cleanup if necessary
        };
    }, []);

    const sendMessage = useCallback((message: object) => {
        webSocketService.sendMessage(message);
    }, []);

    return { status, lastJsonMessage, sendMessage, connect: webSocketService.connect.bind(webSocketService) };
};

export default useWebSocket;
