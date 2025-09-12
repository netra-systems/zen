# 🚀 Demo Deployment Guide - Netra AI Platform

## Quick Start

This guide will help you get the Netra AI demo working in the staging environment with:
- ✅ User interface for entering messages
- ✅ Stable WebSocket connection
- ✅ All 5 agent event emissions (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- ✅ Response delivery to the user
- ✅ **NO AUTHENTICATION REQUIRED** for demo purposes

## Architecture Overview

```
Frontend (React/Next.js)          Backend (FastAPI)
    /demo page                    /api/demo/ws endpoint
        ↓                               ↓
   DemoChat.tsx                  demo_websocket.py
        ↓                               ↓
  useDemoWebSocket()          DemoAgentSimulator
        ↓                               ↓
   WebSocket Events  ←----------→  Agent Events
```

## Features Implemented

### 1. Frontend Demo Interface (`/demo`)
- Industry selection
- Chat interface with message input
- Real-time agent status display
- WebSocket connection indicator
- Message history with responses

### 2. Demo WebSocket Endpoint (`/api/demo/ws`)
- **NO AUTHENTICATION REQUIRED**
- Accepts WebSocket connections directly
- Simulates full agent execution
- Emits all 5 required events:
  - `agent_started` - Agent begins processing
  - `agent_thinking` - Agent reasoning phase
  - `tool_executing` - Tool execution starts
  - `tool_completed` - Tool execution completes
  - `agent_completed` - Final response ready

### 3. Demo-Specific Responses
- Healthcare industry optimization
- Finance industry optimization
- General AI optimization recommendations
- Realistic cost savings and ROI calculations

## Local Testing

### 1. Start Backend Server
```bash
cd netra_backend
python app/main.py
# Server runs on http://localhost:8000
```

### 2. Start Frontend Development Server
```bash
cd frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### 3. Access Demo
Navigate to: http://localhost:3000/demo

### 4. Test WebSocket Connection
1. Select an industry (Healthcare, Finance, etc.)
2. Type a message in the chat input
3. Press Enter or click Send
4. Watch the agent progression through all stages
5. Receive optimization recommendations

## Staging Deployment

### Prerequisites
- GCP project access (netra-staging)
- Cloud Run deployment permissions
- Domain configuration for staging

### Deploy Backend
```bash
# Deploy backend with demo WebSocket endpoint
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local

# Or use the staging-specific script
python scripts/deploy_staging_with_validation.py
```

### Deploy Frontend
```bash
cd frontend
# Build for staging
npm run build:staging

# Deploy to hosting service
# (Vercel, Netlify, or GCP Cloud Run)
```

### Environment Variables

#### Backend (.env.staging)
```env
ENVIRONMENT=staging
# Demo mode - no auth required
DEMO_MODE=true
BYPASS_AUTH=true
```

#### Frontend (.env.staging)
```env
NEXT_PUBLIC_ENVIRONMENT=staging
NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_BYPASS_AUTH=true
```

## Testing the Demo

### WebSocket Event Flow
1. **Connection Established**
   ```json
   {
     "type": "connection_established",
     "connection_id": "uuid",
     "message": "Welcome to Netra AI Demo!"
   }
   ```

2. **User Sends Message**
   ```json
   {
     "type": "chat",
     "message": "Optimize my healthcare AI workloads"
   }
   ```

3. **Agent Events (in order)**
   - agent_started → agent_thinking → tool_executing → tool_completed → agent_completed

4. **Final Response**
   ```json
   {
     "type": "agent_completed",
     "response": "Optimization recommendations...",
     "status": "success"
   }
   ```

### Manual WebSocket Testing
```javascript
// Test in browser console
const ws = new WebSocket('wss://api.staging.netrasystems.ai/api/demo/ws');

ws.onopen = () => {
  console.log('Connected!');
  ws.send(JSON.stringify({
    type: 'chat',
    message: 'Optimize my AI infrastructure'
  }));
};

ws.onmessage = (event) => {
  console.log('Received:', JSON.parse(event.data));
};
```

## Troubleshooting

### WebSocket Connection Issues
- Check CORS configuration allows staging domain
- Verify WebSocket upgrade headers are not stripped
- Ensure Cloud Run allows WebSocket connections
- Check browser console for connection errors

### Missing Agent Events
- Verify demo_websocket.py is imported in route configuration
- Check that all 5 events are being sent in sequence
- Monitor backend logs for event emission

### Authentication Errors
- Demo endpoint should NOT require authentication
- Check BYPASS_AUTH environment variable is set
- Verify /api/demo/ws route bypasses auth middleware

## Security Note

⚠️ **IMPORTANT**: This demo configuration bypasses authentication for demonstration purposes only. 

**DO NOT USE IN PRODUCTION**

For production deployment:
- Remove BYPASS_AUTH flags
- Enable proper authentication
- Use secure WebSocket connections (wss://)
- Implement rate limiting
- Add input validation

## Next Steps

1. **Enhance Demo Features**
   - Add more industry-specific responses
   - Implement file upload simulation
   - Add visual optimization charts

2. **Production Readiness**
   - Re-enable authentication
   - Add proper error handling
   - Implement rate limiting
   - Add monitoring and analytics

3. **Performance Optimization**
   - Implement connection pooling
   - Add caching for common responses
   - Optimize WebSocket message batching

## Support

For issues or questions:
- Check backend logs: `docker logs netra-backend`
- Check frontend console: Browser Developer Tools
- Review WebSocket frames: Network tab → WS
- Contact: support@netrasystems.ai

---

**Demo URL**: https://app.staging.netrasystems.ai/demo
**API Health**: https://api.staging.netrasystems.ai/api/demo/health
**Last Updated**: 2025-01-12