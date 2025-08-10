import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, Zap, Clock, Database, Brain, TrendingUp, 
  AlertCircle, CheckCircle2, Loader2, ChevronRight,
  BarChart3, Sparkles, Settings, Eye
} from 'lucide-react';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { useChatStore } from '@/store/chat';

interface StatusZone {
  type: 'slow' | 'medium' | 'fast';
  label: string;
  content: string | number | React.ReactNode;
  icon: React.ReactNode;
  lastUpdate: number;
  color: string;
}

const AgentStatusPanel: React.FC = () => {
  const { subAgentName, subAgentStatus, isProcessing } = useChatStore();
  const { 
    workflowProgress, 
    agentStatus, 
    activeTools,
    toolExecutionStatus,
    aggregatedResults 
  } = useChatWebSocket();

  const [statusZones, setStatusZones] = useState<StatusZone[]>([]);
  const [expandedPreview, setExpandedPreview] = useState<string | null>(null);
  const [dataPreview, setDataPreview] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({
    recordsProcessed: 0,
    processingRate: 0,
    estimatedTimeRemaining: 0,
    confidenceScore: 0
  });

  // Humor elements
  const processingQuips = [
    "Optimizing the optimizers...",
    "Teaching AI to be more intelligent...",
    "Convincing the models to cooperate...",
    "Negotiating with the neural networks...",
    "Calibrating the crystal ball...",
    "Asking the magic 8-ball for advice...",
    "Consulting the optimization oracle...",
    "Bribing the algorithms with more compute..."
  ];

  const [currentQuip, setCurrentQuip] = useState(processingQuips[0]);

  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setCurrentQuip(processingQuips[Math.floor(Math.random() * processingQuips.length)]);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [isProcessing]);

  // Update status zones based on agent activity
  useEffect(() => {
    const now = Date.now();
    const zones: StatusZone[] = [];

    // Slow zone (10+ seconds updates)
    zones.push({
      type: 'slow',
      label: 'Current Phase',
      content: subAgentName || 'Initializing',
      icon: <Brain className="w-4 h-4" />,
      lastUpdate: now,
      color: 'text-purple-600'
    });

    if (workflowProgress.total_steps > 0) {
      zones.push({
        type: 'slow',
        label: 'Overall Progress',
        content: (
          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <motion.div 
                className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${(workflowProgress.current_step / workflowProgress.total_steps) * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <span className="text-xs font-mono">
              {workflowProgress.current_step}/{workflowProgress.total_steps}
            </span>
          </div>
        ),
        icon: <TrendingUp className="w-4 h-4" />,
        lastUpdate: now,
        color: 'text-blue-600'
      });
    }

    // Medium zone (3-10 seconds updates)
    if (activeTools.length > 0) {
      zones.push({
        type: 'medium',
        label: 'Active Tools',
        content: activeTools.join(', ') || 'None',
        icon: <Settings className="w-4 h-4 animate-spin" />,
        lastUpdate: now,
        color: 'text-green-600'
      });
    }

    if (metrics.recordsProcessed > 0) {
      zones.push({
        type: 'medium',
        label: 'Records Analyzed',
        content: `${metrics.recordsProcessed.toLocaleString()}`,
        icon: <Database className="w-4 h-4" />,
        lastUpdate: now,
        color: 'text-indigo-600'
      });
    }

    // Fast zone (< 3 seconds updates)
    if (toolExecutionStatus !== 'idle') {
      zones.push({
        type: 'fast',
        label: 'Tool Status',
        content: (
          <div className="flex items-center space-x-2">
            {toolExecutionStatus === 'executing' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <CheckCircle2 className="w-3 h-3 text-green-500" />
            )}
            <span className="text-xs capitalize">{toolExecutionStatus}</span>
          </div>
        ),
        icon: <Zap className="w-4 h-4" />,
        lastUpdate: now,
        color: 'text-yellow-600'
      });
    }

    if (metrics.processingRate > 0) {
      zones.push({
        type: 'fast',
        label: 'Processing Rate',
        content: `${metrics.processingRate.toFixed(1)} ops/sec`,
        icon: <Activity className="w-4 h-4" />,
        lastUpdate: now,
        color: 'text-red-600'
      });
    }

    setStatusZones(zones);
  }, [subAgentName, workflowProgress, activeTools, toolExecutionStatus, metrics]);

  // Simulate metrics updates
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setMetrics(prev => ({
          recordsProcessed: prev.recordsProcessed + Math.floor(Math.random() * 100),
          processingRate: 50 + Math.random() * 150,
          estimatedTimeRemaining: Math.max(0, prev.estimatedTimeRemaining - 1),
          confidenceScore: 0.7 + Math.random() * 0.3
        }));
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setMetrics({
        recordsProcessed: 0,
        processingRate: 0,
        estimatedTimeRemaining: 0,
        confidenceScore: 0
      });
    }
  }, [isProcessing]);

  // Generate sample data preview
  useEffect(() => {
    if (isProcessing && Math.random() > 0.7) {
      const sampleData = Array.from({ length: 5 }, (_, i) => ({
        id: `record-${Date.now()}-${i}`,
        model: ['gpt-4', 'claude-2', 'llama-2'][Math.floor(Math.random() * 3)],
        latency: Math.floor(50 + Math.random() * 200),
        tokens: Math.floor(100 + Math.random() * 2000),
        cost: (Math.random() * 0.5).toFixed(4)
      }));
      setDataPreview(sampleData);
    }
  }, [isProcessing, workflowProgress]);

  if (!isProcessing) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-20 right-4 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden z-40"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5" />
            <span className="font-semibold">Agent Intelligence Hub</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-xs">Active</span>
          </div>
        </div>
      </div>

      {/* Status Zones */}
      <div className="p-4 space-y-3">
        {/* Humor Section */}
        <motion.div
          key={currentQuip}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="text-xs text-gray-500 italic text-center py-2 border-b"
        >
          {currentQuip}
        </motion.div>

        {/* Zone Sections */}
        {['slow', 'medium', 'fast'].map(zoneType => {
          const zones = statusZones.filter(z => z.type === zoneType);
          if (zones.length === 0) return null;

          return (
            <div key={zoneType} className="space-y-2">
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                <span className="uppercase font-semibold">
                  {zoneType === 'slow' && '10+ sec'}
                  {zoneType === 'medium' && '3-10 sec'}
                  {zoneType === 'fast' && '< 3 sec'}
                </span>
              </div>
              {zones.map((zone, idx) => (
                <motion.div
                  key={`${zoneType}-${idx}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="bg-gray-50 rounded-lg p-3 border border-gray-100"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-2">
                      <div className={`${zone.color} mt-0.5`}>
                        {zone.icon}
                      </div>
                      <div className="flex-1">
                        <div className="text-xs text-gray-500 mb-1">{zone.label}</div>
                        <div className="text-sm font-medium text-gray-900">
                          {zone.content}
                        </div>
                      </div>
                    </div>
                    <AnimatePresence>
                      {Date.now() - zone.lastUpdate < 1000 && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                          className="w-1.5 h-1.5 bg-green-500 rounded-full"
                        />
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </div>
          );
        })}

        {/* Data Preview Section */}
        {dataPreview.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setExpandedPreview(expandedPreview ? null : 'data')}
              className="flex items-center justify-between w-full text-left"
            >
              <div className="flex items-center space-x-2 text-xs text-gray-600 font-semibold">
                <Eye className="w-3 h-3" />
                <span>DATA PREVIEW</span>
              </div>
              <ChevronRight 
                className={`w-3 h-3 transition-transform ${
                  expandedPreview === 'data' ? 'rotate-90' : ''
                }`}
              />
            </button>
            
            <AnimatePresence>
              {expandedPreview === 'data' && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="mt-2 overflow-hidden"
                >
                  <div className="bg-gray-900 rounded-lg p-3 text-xs font-mono text-green-400 max-h-40 overflow-y-auto">
                    {dataPreview.slice(0, 3).map((item, idx) => (
                      <div key={idx} className="mb-2">
                        <div className="text-blue-400">#{idx + 1}</div>
                        {Object.entries(item).map(([key, value]) => (
                          <div key={key} className="ml-2">
                            <span className="text-gray-500">{key}:</span>{' '}
                            <span className="text-green-400">{value}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                    {dataPreview.length > 3 && (
                      <div className="text-gray-500 text-center">
                        ... {dataPreview.length - 3} more records
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Confidence Indicator */}
        {metrics.confidenceScore > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">Analysis Confidence</span>
              <span className="font-mono font-semibold text-gray-900">
                {(metrics.confidenceScore * 100).toFixed(1)}%
              </span>
            </div>
            <div className="mt-1 bg-gray-200 rounded-full h-1.5">
              <motion.div
                className={`h-1.5 rounded-full ${
                  metrics.confidenceScore > 0.8 
                    ? 'bg-green-500' 
                    : metrics.confidenceScore > 0.6 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${metrics.confidenceScore * 100}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default AgentStatusPanel;