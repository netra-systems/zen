import { w3cwebsocket as W3CWebSocket } from "websocket";
import { config } from "@/config";
import { WebSocketMessage } from "@/types";

class WebSocketService {
  private client: W3CWebSocket | null = null;
  private onMessageCallback: ((message: WebSocketMessage) => void) | null = null;

  public connect(userId: string, onOpen: () => void, onMessage: (message: WebSocketMessage) => void, onError: (error: Error) => void) {
    this.client = new W3CWebSocket(`${config.wsUrl}/v1/${userId}`);

    this.client.onopen = () => {
      console.log("WebSocket Client Connected");
      onOpen();
    };

    this.client.onmessage = (message) => {
      const data = JSON.parse(message.data.toString());
      onMessage(data);
    };

    this.client.onerror = (error) => {
      console.error("WebSocket Error: ", error);
      onError(error);
    };

    this.client.onclose = () => {
      console.log("WebSocket Client Closed");
    };
  }

  public sendMessage(message: WebSocketMessage) {
    if (this.client && this.client.readyState === this.client.OPEN) {
      this.client.send(JSON.stringify(message));
    }
  }

  public disconnect() {
    if (this.client) {
      this.client.close();
    }
  }
}

export const webSocketService = new WebSocketService();
