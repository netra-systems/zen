import { config } from '../../config';

export enum WebSocketStatus {
    Connecting = 'Connecting',
    Open = 'Open',
    Closing = 'Closing',
    Closed = 'Closed',
    Error = 'Error',
}

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private url: string = '';
    public onMessage: ((message: any) => void) | null = null;
    public onStatusChange: ((status: WebSocketStatus) => void) | null = null;

    public connect(token: string, runId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected.');
            return;
        }

        this.url = `${config.api.wsBaseUrl}/agent/${runId}?token=${token}`;
        this.setStatus(WebSocketStatus.Connecting);
        console.log('WebSocket connecting to:', this.url);
        this.ws = new WebSocket(this.url);

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
                // The data received over WebSocket should be a string.
                // We parse it once here. The consumer of `onMessage` will receive an object.
                const parsedData = JSON.parse(event.data);
                if (this.onMessage) {
                    this.onMessage(parsedData);
                }
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

    private setStatus(status: WebSocketStatus): void {
        if (this.onStatusChange) {
            this.onStatusChange(status);
        }
    }
}

