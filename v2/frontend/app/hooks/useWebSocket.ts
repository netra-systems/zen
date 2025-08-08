import { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketStatus } from '@/app/types';
import webSocketService from '@/app/services/websocketService';

const useWebSocket = () => {
    const [status, setStatus] = useState<WebSocketStatus>(WebSocketStatus.Closed);
    const [lastJsonMessage, setLastJsonMessage] = useState<any | null>(null);

    const handleMessage = useCallback((message: any) => {
        setLastJsonMessage(message);
    }, []);

    useEffect(() => {
        webSocketService.onStatusChange(setStatus);
        webSocketService.onMessage(handleMessage);

        // The connection should be initiated elsewhere, for example, in a context or on app load.

        return () => {
            // Disconnecting here might not be desirable for a persistent connection.
        };
    }, [handleMessage]);

    const sendMessage = (message: any) => {
        webSocketService.sendMessage(message);
    };

    return { status, lastJsonMessage, sendMessage, connect: webSocketService.connect.bind(webSocketService) };
};

export default useWebSocket;