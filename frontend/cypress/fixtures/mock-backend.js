// Mock backend server for testing
const express = require('express');
const cors = require('cors');
const http = require('http');
const WebSocket = require('ws');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(cors({
  origin: ['http://localhost:3000', 'http://127.0.0.1:3000'],
  credentials: true
}));

app.use(express.json());

// Health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Agent execution endpoint
app.post('/api/agents/execute', (req, res) => {
  const { message, agent_type = 'general_assistant' } = req.body;
  
  // Mock agent response
  res.json({
    thread_id: 'test-thread-' + Date.now(),
    agent_type,
    status: 'processing',
    websocket_url: 'ws://localhost:8000/ws',
    message: 'Agent execution initiated'
  });

  // Simulate WebSocket events
  setTimeout(() => {
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({
          type: 'agent_started',
          agent_type,
          timestamp: new Date().toISOString()
        }));
      }
    });
  }, 100);

  setTimeout(() => {
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({
          type: 'agent_thinking',
          agent_type,
          message: 'Processing your request...',
          timestamp: new Date().toISOString()
        }));
      }
    });
  }, 500);

  setTimeout(() => {
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({
          type: 'agent_completed',
          agent_type,
          result: `Mock response for: ${message}`,
          timestamp: new Date().toISOString()
        }));
      }
    });
  }, 2000);
});

// WebSocket handling
wss.on('connection', (ws) => {
  console.log('WebSocket client connected');

  ws.on('message', (message) => {
    console.log('WebSocket message received:', message.toString());
  });

  ws.on('close', () => {
    console.log('WebSocket client disconnected');
  });
});

const port = 8000;
server.listen(port, () => {
  console.log(`Mock backend server running on port ${port}`);
  console.log(`WebSocket server running on ws://localhost:${port}/ws`);
});

module.exports = { app, server };