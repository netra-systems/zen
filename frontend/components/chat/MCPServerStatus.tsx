// MCP Server Status Component - Displays server connection status and metrics
// Shows real-time server health, capabilities, and connection information

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Server, 
  Wifi, 
  WifiOff, 
  Activity, 
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  Database
} from 'lucide-react';
import type { MCPServerStatusProps } from '@/types/mcp-types';

// ============================================
// Helper Functions (8 lines max)
// ============================================

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'CONNECTED': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
    case 'CONNECTING': return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
    case 'DISCONNECTED': return <WifiOff className="w-4 h-4 text-gray-500" />;
    case 'ERROR': return <AlertTriangle className="w-4 h-4 text-red-500" />;
    default: return <Server className="w-4 h-4 text-gray-400" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'CONNECTED': return 'border-green-200 bg-green-50 text-green-800';
    case 'CONNECTING': return 'border-blue-200 bg-blue-50 text-blue-800';
    case 'DISCONNECTED': return 'border-gray-200 bg-gray-50 text-gray-800';
    case 'ERROR': return 'border-red-200 bg-red-50 text-red-800';
    default: return 'border-gray-200 bg-gray-50 text-gray-800';
  }
};

const getTransportIcon = (transport: string) => {
  switch (transport) {
    case 'WEBSOCKET': return <Wifi className="w-3 h-3" />;
    case 'HTTP': return <Zap className="w-3 h-3" />;
    default: return <Database className="w-3 h-3" />;
  }
};

const formatLastCheck = (timestamp: string | undefined): string => {
  if (!timestamp) return 'Never';
  const diff = Date.now() - new Date(timestamp).getTime();
  return diff < 60000 ? 'Just now' : `${Math.floor(diff / 60000)}m ago`;
};

// ============================================
// Sub-components (8 lines max)
// ============================================

const ServerCard: React.FC<{ server: any; compact?: boolean }> = ({ server, compact = false }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    className={`p-3 rounded-lg border ${getStatusColor(server.status)}`}
  >
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        {getStatusIcon(server.status)}
        <span className="font-medium text-sm">{server.name}</span>
        <span className="flex items-center space-x-1 text-xs opacity-75">
          {getTransportIcon(server.transport)}
          <span>{server.transport}</span>
        </span>
      </div>
      {!compact && (
        <div className="text-xs opacity-75">
          <Clock className="w-3 h-3 inline mr-1" />
          {formatLastCheck(server.last_health_check)}
        </div>
      )}
    </div>
    
    {!compact && server.capabilities && (
      <div className="mt-2 text-xs opacity-75">
        {Object.keys(server.capabilities).length} capabilities
      </div>
    )}
  </motion.div>
);

const StatusSummary: React.FC<{ servers: any[] }> = ({ servers }) => {
  const summary = useMemo(() => {
    const connected = servers.filter(s => s.status === 'CONNECTED').length;
    const total = servers.length;
    const hasErrors = servers.some(s => s.status === 'ERROR');
    return { connected, total, hasErrors };
  }, [servers]);

  return (
    <div className="flex items-center space-x-2 text-sm">
      <Server className="w-4 h-4 text-gray-500" />
      <span className="font-medium">
        {summary.connected}/{summary.total} Connected
      </span>
      {summary.hasErrors && (
        <AlertTriangle className="w-4 h-4 text-red-500" />
      )}
    </div>
  );
};

const ConnectionIndicator: React.FC<{ connections: any[] }> = ({ connections }) => {
  const activeConnections = connections.filter(c => c.status === 'CONNECTED');
  
  return (
    <div className="flex items-center space-x-1">
      {activeConnections.slice(0, 3).map(conn => (
        <motion.div
          key={conn.id}
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="w-2 h-2 bg-green-500 rounded-full"
        />
      ))}
      {activeConnections.length > 3 && (
        <span className="text-xs text-gray-500">+{activeConnections.length - 3}</span>
      )}
    </div>
  );
};

// ============================================
// Main Component
// ============================================

export const MCPServerStatus: React.FC<MCPServerStatusProps> = ({
  servers = [],
  connections = [],
  compact = false,
  className = ''
}) => {
  if (servers.length === 0) {
    return (
      <div className={`mcp-server-status ${className}`}>
        <div className="flex items-center space-x-2 text-gray-500 text-sm">
          <Server className="w-4 h-4" />
          <span>No MCP servers</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`mcp-server-status ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <StatusSummary servers={servers} />
        {!compact && <ConnectionIndicator connections={connections} />}
      </div>

      <AnimatePresence>
        {servers.map((server) => (
          <div key={server.id} className="mb-2 last:mb-0">
            <ServerCard server={server} compact={compact} />
          </div>
        ))}
      </AnimatePresence>

      {compact && connections.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{connections.length} active sessions</span>
            <ConnectionIndicator connections={connections} />
          </div>
        </div>
      )}
    </div>
  );
};

MCPServerStatus.displayName = 'MCPServerStatus';