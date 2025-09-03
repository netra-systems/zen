/**
 * AgentStatusIndicator - Real-time agent status with smooth 60fps animations
 * Displays agent execution progress with 100ms update granularity
 */
'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Cpu, Zap, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { cn } from '@/lib/utils';
import { agentUpdateStream, type AgentUpdate, type StreamBatch } from '@/services/agent-update-stream';
import { PerformanceMetrics } from '@/types/performance-metrics';

interface AgentStatusIndicatorProps {
  agentId?: string;
  position?: 'top-right' | 'bottom-right' | 'floating';
  showProgress?: boolean;
  showToolExecution?: boolean;
  compact?: boolean;
}

interface VisualState {
  status: AgentUpdate['status'];
  progress: number;
  toolName: string | null;
  lastUpdate: number;
  isAnimating: boolean;
}


const AgentStatusIndicator: React.FC<AgentStatusIndicatorProps> = ({
  agentId,
  position = 'top-right',
  showProgress = true,
  showToolExecution = true,
  compact = false
}) => {
  const [visualState, setVisualState] = useState<VisualState>(createInitialState());
  const [isVisible, setIsVisible] = useState(false);
  const [metrics, setMetrics] = useState<PerformanceMetrics>(createInitialMetrics());
  
  const rafRef = useRef<number | null>(null);
  const lastFrameTime = useRef(0);
  const updateBuffer = useRef<AgentUpdate[]>([]);

  // ============================================
  // Stream Subscription Management
  // ============================================

  useEffect(() => {
    const subscriptionId = agentUpdateStream.subscribe(
      handleStreamBatch,
      agentId ? createAgentFilter(agentId) : undefined
    );

    agentUpdateStream.start();

    return () => {
      agentUpdateStream.unsubscribe(subscriptionId);
      cancelAnimationFrame(rafRef.current || 0);
    };
  }, [agentId]);

  const handleStreamBatch = (batch: StreamBatch): void => {
    updateBuffer.current.push(...batch.updates);
    scheduleRenderUpdate();
  };

  const createAgentFilter = (targetAgentId: string) => (update: AgentUpdate): boolean => {
    return update.agentId === targetAgentId;
  };

  // ============================================
  // RAF-Optimized Rendering
  // ============================================

  const scheduleRenderUpdate = (): void => {
    if (rafRef.current) return;
    
    rafRef.current = requestAnimationFrame(processRenderUpdate);
  };

  const processRenderUpdate = (timestamp: number): void => {
    const startTime = performance.now();
    
    if (updateBuffer.current.length > 0) {
      const latestUpdate = getLatestUpdate();
      updateVisualState(latestUpdate);
      updateBuffer.current = [];
    }
    
    updatePerformanceMetrics(timestamp, startTime);
    rafRef.current = null;
  };

  const getLatestUpdate = (): AgentUpdate => {
    return updateBuffer.current[updateBuffer.current.length - 1];
  };

  const updateVisualState = (update: AgentUpdate): void => {
    setVisualState(prev => ({
      status: update.status,
      progress: update.progress || prev.progress,
      toolName: update.toolName || prev.toolName,
      lastUpdate: update.timestamp,
      isAnimating: true
    }));
    
    setIsVisible(update.status !== 'complete');
    
    // Reset animation flag after animation duration
    setTimeout(() => {
      setVisualState(prev => ({ ...prev, isAnimating: false }));
    }, 300);
  };

  // ============================================
  // Performance Monitoring
  // ============================================

  const updatePerformanceMetrics = (timestamp: number, startTime: number): void => {
    const frameRate = calculateFrameRate(timestamp);
    const renderTime = performance.now() - startTime;
    const updateLatency = timestamp - (updateBuffer.current[0]?.timestamp || timestamp);
    
    setMetrics({
      renderCount: 0,
      lastRenderTime: timestamp,
      averageResponseTime: 0,
      wsLatency: updateLatency,
      memoryUsage: 0,
      fps: frameRate,
      componentRenderTimes: new Map<string, number>(),
      errorCount: 0,
      cacheHitRate: 0,
      renderTime
    });
  };

  const calculateFrameRate = (timestamp: number): number => {
    if (lastFrameTime.current === 0) {
      lastFrameTime.current = timestamp;
      return 60;
    }
    
    const delta = timestamp - lastFrameTime.current;
    lastFrameTime.current = timestamp;
    
    return Math.round(1000 / delta);
  };

  // ============================================
  // Visual Configuration
  // ============================================

  const statusConfig = useMemo(() => getStatusConfiguration(visualState.status), [visualState.status]);
  const positionClasses = useMemo(() => getPositionClasses(position), [position]);
  const progressValue = useMemo(() => Math.min(Math.max(visualState.progress, 0), 100), [visualState.progress]);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.8, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.8, y: -20 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={cn(
          'fixed z-50 bg-white rounded-lg shadow-2xl border border-gray-200',
          positionClasses,
          compact ? 'p-3' : 'p-4'
        )}
      >
        <StatusHeader 
          statusConfig={statusConfig}
          isAnimating={visualState.isAnimating}
          compact={compact}
        />
        
        {showProgress && (
          <ProgressSection 
            progress={progressValue}
            statusConfig={statusConfig}
            compact={compact}
          />
        )}
        
        {showToolExecution && visualState.toolName && (
          <ToolExecutionSection 
            toolName={visualState.toolName}
            compact={compact}
          />
        )}
        
        <MetricsFooter 
          metrics={metrics}
          compact={compact}
        />
      </motion.div>
    </AnimatePresence>
  );
};

// ============================================
// Sub-Components
// ============================================

const StatusHeader: React.FC<{
  statusConfig: ReturnType<typeof getStatusConfiguration>;
  isAnimating: boolean;
  compact: boolean;
}> = ({ statusConfig, isAnimating, compact }) => (
  <div className="flex items-center space-x-3">
    <motion.div
      animate={isAnimating ? { scale: [1, 1.2, 1], rotate: [0, 180, 360] } : {}}
      transition={{ duration: 0.6 }}
      className={cn('p-2 rounded-full', statusConfig.bgColor)}
    >
      <statusConfig.Icon className={cn('w-4 h-4', statusConfig.textColor)} />
    </motion.div>
    
    {!compact && (
      <div>
        <div className={cn('font-semibold text-sm', statusConfig.textColor)}>
          {statusConfig.label}
        </div>
        <div className="text-xs text-gray-500">Agent Processing</div>
      </div>
    )}
  </div>
);

const ProgressSection: React.FC<{
  progress: number;
  statusConfig: ReturnType<typeof getStatusConfiguration>;
  compact: boolean;
}> = ({ progress, statusConfig, compact }) => (
  <div className={cn('mt-3', compact && 'mt-2')}>
    <div className="flex justify-between items-center mb-1">
      <span className="text-xs text-gray-600">Progress</span>
      <span className="text-xs font-semibold">{progress.toFixed(0)}%</span>
    </div>
    <div className="w-full bg-gray-200 rounded-full h-2">
      <motion.div
        className={cn('h-2 rounded-full', statusConfig.bgColor)}
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  </div>
);

const ToolExecutionSection: React.FC<{
  toolName: string;
  compact: boolean;
}> = ({ toolName, compact }) => (
  <div className={cn('mt-3 p-2 bg-gray-50 rounded', compact && 'mt-2 p-1')}>
    <div className="flex items-center space-x-2">
      <Cpu className="w-3 h-3 text-blue-500" />
      <span className="text-xs text-gray-700">
        Executing: <span className="font-semibold">{toolName}</span>
      </span>
    </div>
  </div>
);

const MetricsFooter: React.FC<{
  metrics: PerformanceMetrics;
  compact: boolean;
}> = ({ metrics, compact }) => {
  if (compact) return null;
  
  return (
    <div className="mt-3 pt-2 border-t border-gray-100">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{metrics.fps}fps</span>
        <span>{metrics.renderTime.toFixed(1)}ms</span>
      </div>
    </div>
  );
};

// ============================================
// Configuration Functions
// ============================================

const getStatusConfiguration = (status: AgentUpdate['status']) => {
  const configs = {
    thinking: {
      Icon: Brain,
      label: 'Thinking',
      bgColor: 'bg-blue-100',
      textColor: 'text-blue-700'
    },
    executing: {
      Icon: Zap,
      label: 'Executing',
      bgColor: 'bg-yellow-100',
      textColor: 'text-yellow-700'
    },
    tool_running: {
      Icon: Cpu,
      label: 'Tool Running',
      bgColor: 'bg-purple-100',
      textColor: 'text-purple-700'
    },
    complete: {
      Icon: CheckCircle,
      label: 'Complete',
      bgColor: 'bg-green-100',
      textColor: 'text-green-700'
    },
    error: {
      Icon: AlertCircle,
      label: 'Error',
      bgColor: 'bg-red-100',
      textColor: 'text-red-700'
    }
  };
  
  return configs[status] || configs.thinking;
};

const getPositionClasses = (position: string): string => {
  const positions = {
    'top-right': 'top-4 right-4',
    'bottom-right': 'bottom-4 right-4',
    'floating': 'top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2'
  };
  
  return positions[position as keyof typeof positions] || positions['top-right'];
};

const createInitialState = (): VisualState => ({
  status: 'thinking',
  progress: 0,
  toolName: null,
  lastUpdate: 0,
  isAnimating: false
});

const createInitialMetrics = (): PerformanceMetrics => ({
  renderCount: 0,
  lastRenderTime: 0,
  averageResponseTime: 0,
  wsLatency: 0,
  memoryUsage: 0,
  fps: 60,
  componentRenderTimes: new Map<string, number>(),
  errorCount: 0,
  cacheHitRate: 0
});

export default AgentStatusIndicator;