// MCP Server Status Component - Displays server connection status and metrics
// Shows real-time server health, capabilities, and connection information

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
// Import icons with fallbacks to avoid undefined issues
import * as LucideIcons from 'lucide-react';
const { 
  Server, 
  Wifi, 
  WifiOff, 
  Activity, 
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  Database
} = LucideIcons;
import type { MCPServerStatusProps } from '@/types/mcp-types';

// ============================================
// Helper Functions (8 lines max)
// ============================================

const getStatusIcon = (status: string) => {
  const defaultIcon = <div className="w-4 h-4 bg-gray-400 rounded" />;
  switch (status) {
    case 'CONNECTED': return CheckCircle2 ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <div className="w-4 h-4 bg-green-500 rounded-full" />;
    case 'CONNECTING': return Activity ? <Activity className="w-4 h-4 text-blue-500 animate-pulse" /> : <div className="w-4 h-4 bg-blue-500 rounded animate-pulse" />;
    case 'DISCONNECTED': return WifiOff ? <WifiOff className="w-4 h-4 text-gray-500" /> : <div className="w-4 h-4 bg-gray-500 rounded" />;
    case 'ERROR': return AlertTriangle ? <AlertTriangle className="w-4 h-4 text-red-500" /> : <div className="w-4 h-4 bg-red-500 rounded" />;
    default: return Server ? <Server className="w-4 h-4 text-gray-400" /> : defaultIcon;
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
  const defaultIcon = <div className="w-3 h-3 bg-gray-400 rounded" />;
  switch (transport) {
    case 'WEBSOCKET': return Wifi ? <Wifi className="w-3 h-3" /> : <div className="w-3 h-3 bg-blue-500 rounded" />;
    case 'HTTP': return Zap ? <Zap className="w-3 h-3" /> : <div className="w-3 h-3 bg-yellow-500 rounded" />;
    default: return Database ? <Database className="w-3 h-3" /> : defaultIcon;
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
          {Clock ? <Clock className="w-3 h-3 inline mr-1" /> : <div className="w-3 h-3 bg-gray-400 rounded inline mr-1" />}
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
      {Server ? <Server className="w-4 h-4 text-gray-500" /> : <div className="w-4 h-4 bg-gray-500 rounded" />}
      <span className="font-medium">
        {summary.connected}/{summary.total} Connected
      </span>
      {summary.hasErrors && (
        AlertTriangle ? <AlertTriangle className="w-4 h-4 text-red-500" /> : <div className="w-4 h-4 bg-red-500 rounded" />
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
          {Server ? <Server className="w-4 h-4" /> : <div className="w-4 h-4 bg-gray-400 rounded" />}
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