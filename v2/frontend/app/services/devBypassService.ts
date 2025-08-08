import { useWebSocket } from './websocket';

export const useDevWebSocket = (onMessage: (message: any) => void) => {
    const { lastJsonMessage } = useWebSocket();
    if (lastJsonMessage) {
        onMessage(lastJsonMessage);
    }
};