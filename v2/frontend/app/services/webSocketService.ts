
import { w3cwebsocket as W3CWebSocket } from "websocket";

class WebSocketService {
    private client: W3CWebSocket | null = null;
    private static instance: WebSocketService;
    private messageListeners: ((message: any) => void)[] = [];
    private connectionListeners: ((isConnected: boolean) => void)[] = [];
    private isConnected: boolean = false;

    private constructor() {}

    public static getInstance(): WebSocketService {
        if (!WebSocketService.instance) {
            WebSocketService.instance = new WebSocketService();
        }
        return WebSocketService.instance;
    }

    public connect(url: string): void {
        if (this.client && this.client.readyState === this.client.OPEN) {
            return;
        }

        this.client = new W3CWebSocket(url);

        this.client.onopen = () => {
            console.log("WebSocket Client Connected");
            this.isConnected = true;
            this.connectionListeners.forEach(listener => listener(true));
            this.client?.send("handshake");
        };

        this.client.onmessage = (message) => {
            if (message.data === "handshake_ack") {
                console.log("WebSocket handshake successful");
                return;
            }
            this.messageListeners.forEach(listener => listener(message));
        };

        this.client.onclose = () => {
            console.log("WebSocket Client Closed");
            this.isConnected = false;
            this.connectionListeners.forEach(listener => listener(false));
        };

        this.client.onerror = (error) => {
            console.error("WebSocket Error", error);
        };
    }

    public addMessageListener(listener: (message: any) => void): void {
        this.messageListeners.push(listener);
    }

    public removeMessageListener(listener: (message: any) => void): void {
        this.messageListeners = this.messageListeners.filter(l => l !== listener);
    }

    public addConnectionListener(listener: (isConnected: boolean) => void): void {
        this.connectionListeners.push(listener);
    }

    public removeConnectionListener(listener: (isConnected: boolean) => void): void {
        this.connectionListeners = this.connectionListeners.filter(l => l !== listener);
    }

    public sendMessage(message: string): void {
        if (this.client && this.client.readyState === this.client.OPEN) {
            this.client.send(message);
        }
    }

    public disconnect(): void {
        if (this.client) {
            this.client.close();
        }
    }
}

export default WebSocketService.getInstance();
