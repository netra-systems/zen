# Frontend Agent Testing Guide - Netra Apex

## ✅ Complete Setup Ready

The frontend service is now fully configured and ready for agent testing with all backend services running on Podman.

## 🚀 Access Your Netra Apex Application

### Main Interface
**Frontend Application**: http://localhost:3001

### All Service Endpoints
| Service | Endpoint | Purpose |
|---------|----------|---------|
| **Frontend** | http://localhost:3001 | Main web interface for agent testing |
| **Frontend Health** | http://localhost:3001/api/health | Frontend service status |
| **Backend API** | http://localhost:8480 | Backend service API |
| **Auth Service** | http://localhost:8482 | Authentication service |
| **PostgreSQL** | localhost:8090 | Database (netra:netra123@netra_dev) |
| **Redis** | localhost:8410 | Cache and sessions |
| **ClickHouse** | localhost:8492 | Analytics database |

## 🤖 Testing Agents

### 1. Access the Web Interface
Open your browser and navigate to: **http://localhost:3001**

### 2. Available Agent Testing Features
The frontend connects to your Podman backend services and provides:

- **Chat Interface**: Interactive agent conversations
- **WebSocket Support**: Real-time agent responses  
- **Agent Management**: Create, configure, and run agents
- **Data Analysis**: View agent outputs and insights
- **Configuration**: Adjust agent parameters and behavior

### 3. WebSocket Connection
The frontend is configured to connect to the backend WebSocket at:
- **WebSocket URL**: `ws://localhost:8480/ws`
- **Real-time updates**: Agent status, progress, and results
- **Live chat**: Interactive agent conversations

### 4. Agent Workflows
You can test various agent types:
- **Data Analysis Agents**: Process and analyze datasets
- **Optimization Agents**: Recommend improvements
- **Research Agents**: Gather and synthesize information
- **Custom Agents**: Create specialized workflows

## 📊 System Status

Check all services at any time:
```bash
bash scripts/podman_mac_services.sh status
```

**Current Status** (all healthy ✅):
- Frontend: Running on port 3001
- Backend: Running on port 8480
- Auth: Running on port 8482
- PostgreSQL: Running on port 8090
- Redis: Running on port 8410
- ClickHouse: Running on port 8492

## 🔧 Management Commands

### Service Management
```bash
# Check status of all services
bash scripts/podman_mac_services.sh status

# Restart backend services  
bash scripts/podman_mac_services.sh restart

# View service logs
bash scripts/podman_mac_services.sh logs

# Stop all services
bash scripts/podman_mac_services.sh stop
```

### Frontend Management
The frontend runs locally for faster development:

```bash
# Start frontend (if not running)
cd frontend && npm run dev

# Check frontend health
curl http://localhost:3001/api/health

# View frontend logs
# Check the terminal where npm run dev is running
```

## 🔍 Troubleshooting Agent Testing

### If Agents Don't Respond
1. **Check Backend Connection**:
   ```bash
   curl http://localhost:8480/health
   ```

2. **Check WebSocket Connection**:
   - Open browser dev tools (F12)
   - Go to Network tab
   - Look for WebSocket connections to `ws://localhost:8480/ws`

3. **Check Auth Service**:
   ```bash
   curl http://localhost:8482/health
   ```

### If Frontend Won't Load
1. **Check if frontend is running**:
   ```bash
   curl -I http://localhost:3001
   ```

2. **Restart frontend**:
   ```bash
   cd frontend && npm run dev
   ```

3. **Check for port conflicts**:
   ```bash
   lsof -i :3001
   ```

### If Database Connections Fail
1. **Check PostgreSQL**:
   ```bash
   PGPASSWORD=netra123 psql -h localhost -p 8090 -U netra -d netra_dev -c "SELECT version();"
   ```

2. **Check Redis**:
   ```bash
   redis-cli -h localhost -p 8410 ping
   ```

3. **Restart services**:
   ```bash
   bash scripts/podman_mac_services.sh restart
   ```

## 🧪 Agent Testing Scenarios

### Scenario 1: Basic Agent Chat
1. Open http://localhost:3001
2. Navigate to the chat interface
3. Start a conversation with an agent
4. Verify real-time responses via WebSocket

### Scenario 2: Data Analysis Agent  
1. Upload or input data through the interface
2. Select a data analysis agent
3. Monitor progress in real-time
4. Review analysis results and visualizations

### Scenario 3: Multi-Agent Workflow
1. Create a complex workflow with multiple agents
2. Monitor agent coordination and handoffs
3. Verify data persistence across agent steps
4. Review final consolidated results

### Scenario 4: Agent Configuration
1. Access agent configuration settings
2. Modify parameters and behavior
3. Test different agent personalities/approaches
4. Save and reuse successful configurations

## 🔐 Authentication Testing

The system includes OAuth and local authentication:
- **Local Development**: Uses development tokens
- **OAuth Integration**: Google OAuth configured
- **Session Management**: Redis-backed sessions
- **Security**: JWT tokens with proper validation

## 📈 Performance Monitoring

Monitor agent performance through:
- **Frontend**: Real-time progress indicators
- **Backend Logs**: Detailed execution traces
- **Database**: Query performance and data growth
- **Memory Usage**: Agent resource consumption

## 🎯 Next Steps

Your Netra Apex system is now fully operational for agent testing:

1. **Start Testing**: Open http://localhost:3001 and begin agent interactions
2. **Explore Features**: Test different agent types and configurations  
3. **Monitor Performance**: Use the status commands to track system health
4. **Iterate**: Modify configurations and test new agent workflows

## 🚀 Ready to Test!

**Main URL**: http://localhost:3001

Your complete AI agent testing environment is running and healthy. All backend services are containerized with Podman, and the frontend provides a rich interface for agent interaction and monitoring.

Happy agent testing! 🤖✨