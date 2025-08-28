// Connection metrics display component
// Shows connection quality, latency, and other performance metrics

import React from 'react';
import { ConnectionMetrics, formatLatency, formatDuration, getConnectionQuality } from '@/utils/connection-status-utils';

interface ConnectionMetricsProps {
  metrics: ConnectionMetrics;
  isExpanded?: boolean;
  className?: string;
}

// Format reconnection display
const formatReconnections = (count: number, lastTime: number | null): string => {
  if (count === 0) return 'No reconnections';
  
  const timeDisplay = lastTime 
    ? ` (last: ${formatDuration(Date.now() - lastTime)} ago)`
    : '';
  
  return `${count} reconnection${count > 1 ? 's' : ''}${timeDisplay}`;
};

// Render latency with quality indicator
const LatencyDisplay: React.FC<{ latency: number | null }> = ({ latency }) => {
  const { quality, color } = getConnectionQuality(latency);
  const latencyText = formatLatency(latency);
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-zinc-600">Latency:</span>
      <span className={`text-xs font-medium ${color}`}>
        {latencyText}
      </span>
      {quality !== 'unknown' && (
        <span className="text-xs text-zinc-500 capitalize">
          ({quality})
        </span>
      )}
    </div>
  );
};

// Render connection duration
const DurationDisplay: React.FC<{ duration: number }> = ({ duration }) => (
  <div className="flex items-center gap-2">
    <span className="text-xs text-zinc-600">Connected:</span>
    <span className="text-xs font-medium text-zinc-700">
      {formatDuration(duration)}
    </span>
  </div>
);

// Render message counts
const MessageCountDisplay: React.FC<{ sent: number; received: number }> = ({ sent, received }) => (
  <div className="flex items-center gap-2">
    <span className="text-xs text-zinc-600">Messages:</span>
    <span className="text-xs font-medium text-zinc-700">
      ↑{sent} ↓{received}
    </span>
  </div>
);

// Render reconnection info
const ReconnectionDisplay: React.FC<{ count: number; lastTime: number | null }> = ({ count, lastTime }) => {
  const reconnectionText = formatReconnections(count, lastTime);
  const textColor = count > 0 ? 'text-yellow-600' : 'text-emerald-600';
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-zinc-600">Stability:</span>
      <span className={`text-xs font-medium ${textColor}`}>
        {reconnectionText}
      </span>
    </div>
  );
};

const ConnectionMetrics: React.FC<ConnectionMetricsProps> = ({
  metrics,
  isExpanded = false,
  className = ''
}) => {
  if (!isExpanded) return null;
  
  return (
    <div className={`p-3 space-y-2 border-t border-zinc-200 ${className}`}>
      <div className="text-xs font-medium text-zinc-700 mb-2">
        Connection Details
      </div>
      
      <div className="grid grid-cols-1 gap-2">
        <LatencyDisplay latency={metrics.latency} />
        <DurationDisplay duration={metrics.connectionDuration} />
        <MessageCountDisplay 
          sent={metrics.messagesSent} 
          received={metrics.messagesReceived} 
        />
        <ReconnectionDisplay 
          count={metrics.reconnectionCount} 
          lastTime={metrics.lastReconnectTime} 
        />
      </div>
    </div>
  );
};

ConnectionMetrics.displayName = 'ConnectionMetrics';

export default ConnectionMetrics;