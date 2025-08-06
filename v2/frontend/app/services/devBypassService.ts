
import { config } from '../config';

export const connectToDevWebSocket = (onMessage: (message: any) => void) => {
    const ws = new WebSocket(`${config.api.wsBaseUrl}/ws/dev`);

    ws.onmessage = (event) => {
        onMessage(event.data);
    };

    return ws;
};
