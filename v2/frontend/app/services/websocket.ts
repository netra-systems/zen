import { WebSocketStatus } from '@/types';
import config from '@/types';

class WebSocketService {
    private static instance: WebSocketService;
    private ws: WebSocket | null = null;
    private status: WebSocketStatus = WebSocketStatus.Closed;
    private onStatusChangeCallbacks: ((status: WebSocketStatus) => void)[] = [];
    private onMessageCallbacks: ((message: any) => void)[] = [];

    private constructor() {}

    public static getInstance(): WebSocketService {
        if (!WebSocketService.instance) {
            WebSocketService.instance = new WebSocketService();
        }
        return WebSocketService.instance;
    }

    public connect(token: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected.');
            return;
        }

        const url = `${config.api.wsBaseUrl}/ws?token=${token}`;
        this.setStatus(WebSocketStatus.Connecting);
        console.log('WebSocket connecting to:', url);
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('WebSocket connection established.');
            this.setStatus(WebSocketStatus.Open);
        };

        this.ws.onclose = () => {
            console.log('WebSocket connection closed.');
            this.setStatus(WebSocketStatus.Closed);
        };

        this.ws.onerror = (event) => {
            console.error('WebSocket error:', event);
            this.setStatus(WebSocketStatus.Error);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.onMessageCallbacks.forEach(callback => callback(message));
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error, 'Received data:', event.data);
            }
        };
    }

    public disconnect(): void {
        if (this.ws) {
            console.log('Disconnecting WebSocket.');
            this.ws.close();
        }
    }

    public sendMessage(message: object): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not open. Cannot send message.');
        }
    }

    public onStatusChange(callback: (status: WebSocketStatus) => void): void {
        this.onStatusChangeCallbacks.push(callback);
    }

    public onMessage(callback: (message: any) => void): void {
        this.onMessageCallbacks.push(callback);
    }

    private setStatus(status: WebSocketStatus): void {
        this.status = status;
        this.onStatusChangeCallbacks.forEach(callback => callback(status));
    }
}

export default WebSocketService.getInstance();