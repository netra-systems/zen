const EventEmitter = require('events');

let lastInstance = null;

class MockWebSocket extends EventEmitter {
  constructor(url) {
    super();
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    lastInstance = this;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.emit('open');
    }, 0);
  }

  send(data) {
    // Mock send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.emit('close');
  }

  static get lastInstance() {
    return lastInstance;
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

class MockWebSocketServer extends EventEmitter {
  constructor(options, callback) {
    super();
    if (callback) {
      callback();
    }
  }

  close(callback) {
    if (callback) {
      callback();
    }
  }
}

module.exports = {
  WebSocket: MockWebSocket,
  Server: MockWebSocketServer, // Note: Jest documentation uses Server, not WebSocketServer
  WebSocketServer: MockWebSocketServer,
};