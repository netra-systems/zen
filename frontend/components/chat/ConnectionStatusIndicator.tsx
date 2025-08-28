// Main connection status indicator component
// Real-time WebSocket connection status display with glassmorphic design

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocketContext } from '@/providers/WebSocketProvider';
import { webSocketService } from '@/services/webSocketService';
import ConnectionMetricsComponent from './ConnectionMetrics';
import { 
  ConnectionState, 
  ConnectionMetrics as IConnectionMetrics,
  getConnectionState, 
  getStatusInfo 
} from '@/utils/connection-status-utils';

// Import icons individually to avoid potential undefined issues
import * as LucideIcons from 'lucide-react';
const { ChevronDown, Wifi, WifiOff, RotateCw } = LucideIcons;

interface ConnectionStatusIndicatorProps {
  className?: string;
  compact?: boolean;
}

// Status dot component with pulsing animation
const StatusDot: React.FC<{ 
  state: ConnectionState;
  iconClass: string;
}> = ({ state, iconClass }) => {
  const shouldPulse = state === 'connecting' || state === 'reconnecting';
  
  return (
    <div className="relative">
      <div className={`w-2 h-2 rounded-full ${iconClass}`} />
      {shouldPulse && (
        <div className={`absolute inset-0 w-2 h-2 rounded-full ${iconClass} animate-ping opacity-75`} />
      )}
    </div>
  );
};

// Status icon component - with null checks
const StatusIcon: React.FC<{ state: ConnectionState }> = ({ state }) => {
  const iconProps = { size: 14, className: "text-zinc-600" };
  
  switch (state) {
    case 'connected':
      return Wifi ? <Wifi {...iconProps} className="text-emerald-600" /> : <div className="w-3 h-3 bg-emerald-600 rounded" />;
    case 'connecting':
    case 'reconnecting':
      return RotateCw ? <RotateCw {...iconProps} className="animate-spin" /> : <div className="w-3 h-3 bg-blue-600 rounded animate-spin" />;
    case 'disconnected':
    case 'error':
    default:
      return WifiOff ? <WifiOff {...iconProps} className="text-red-600" /> : <div className="w-3 h-3 bg-red-600 rounded" />;
  }
};

// Connection status hook for metrics tracking
const useConnectionMetrics = (): IConnectionMetrics => {
  const [metrics, setMetrics] = useState<IConnectionMetrics>({
    latency: null,
    reconnectionCount: 0,
    lastReconnectTime: null,
    connectionDuration: 0,
    messagesSent: 0,
    messagesReceived: 0
  });
  
  const [connectionStartTime, setConnectionStartTime] = useState<number | null>(null);
  const { status } = useWebSocketContext();
  
  // Track connection duration
  useEffect(() => {
    if (status === 'OPEN' && !connectionStartTime) {
      setConnectionStartTime(Date.now());
    } else if (status !== 'OPEN') {
      setConnectionStartTime(null);
    }
  }, [status, connectionStartTime]);
  
  // Update connection duration
  useEffect(() => {
    if (!connectionStartTime) return;
    
    const interval = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        connectionDuration: Date.now() - connectionStartTime
      }));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [connectionStartTime]);
  
  return metrics;
};

const ConnectionStatusIndicator: React.FC<ConnectionStatusIndicatorProps> = ({
  className = '',
  compact = false
}) => {
  const { status } = useWebSocketContext();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const metrics = useConnectionMetrics();
  
  // Get current connection state
  const connectionState = getConnectionState(status, isReconnecting);
  const statusInfo = getStatusInfo(connectionState);
  
  // Handle expand/collapse
  const toggleExpanded = useCallback(() => {
    if (!compact) {
      setIsExpanded(prev => !prev);
    }
  }, [compact]);
  
  // Track reconnection state
  useEffect(() => {
    const currentState = webSocketService.getState();
    setIsReconnecting(currentState === 'reconnecting');
  }, [status]);
  
  // Compact version for minimal space usage
  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <StatusDot state={connectionState} iconClass={statusInfo.iconClass} />
        <StatusIcon state={connectionState} />
      </div>
    );
  }
  
  return (
    <div className={`relative ${className}`}>
      <motion.div
        className="glassmorphic-card cursor-pointer select-none"
        onClick={toggleExpanded}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        transition={{ duration: 0.2 }}
      >
        <div className="flex items-center justify-between p-3">
          <div className="flex items-center gap-3">
            <StatusDot state={connectionState} iconClass={statusInfo.iconClass} />
            <StatusIcon state={connectionState} />
            <div className="flex flex-col">
              <span className={`text-sm font-medium ${statusInfo.colorClass}`}>
                {statusInfo.displayText}
              </span>
              {connectionState === 'connected' && metrics.latency !== null && (
                <span className="text-xs text-zinc-500">
                  {Math.round(metrics.latency)}ms
                </span>
              )}
            </div>
          </div>
          
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            {ChevronDown ? <ChevronDown size={16} className="text-zinc-500" /> : <div className="w-4 h-4 bg-zinc-500" />}
          </motion.div>
        </div>
        
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <ConnectionMetricsComponent metrics={metrics} isExpanded={true} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

ConnectionStatusIndicator.displayName = 'ConnectionStatusIndicator';

export default ConnectionStatusIndicator;