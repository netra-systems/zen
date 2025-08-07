const EventEmitter = require('events');

class MockWebSocket extends EventEmitter {
  constructor(url) {
    super();
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    MockWebSocket.lastInstance = this;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.emit('open');
    }, 0);
  }

  send(data) {}

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.emit('close');
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;
MockWebSocket.lastInstance = null;

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
  Server: MockWebSocketServer,
  WebSocketServer: MockWebSocketServer,
};
