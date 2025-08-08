
import webSocketService from './websocket';

export const connectToDevWebSocket = (onMessage: (message: string) => void) => {
    webSocketService.onMessage(onMessage);
};
