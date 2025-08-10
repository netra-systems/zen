import React, { useEffect, useState } from 'react';
import { useChatStore } from '@/store/chat';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  Bot, 
  Clock, 
  Layers, 
  Pause, 
  Settings, 
  Sparkles,
  Timer,
  TrendingUp,
  Zap,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface EnhancedChatHeaderProps {
  metrics?: {
    currentAgent: string | null;
    totalDuration: number;
    stepCount: number;
  };
  onToggleDetails?: () => void;
  showDetails?: boolean;
}

export const EnhancedChatHeader: React.FC<EnhancedChatHeaderProps> = ({ 
  metrics,
  onToggleDetails,
  showDetails = false 
}) => {
  const { subAgentName, subAgentStatus, isProcessing } = useChatStore();
  const [elapsedTime, setElapsedTime] = useState(0);
  const [thoughtCycle, setThoughtCycle] = useState(0);
  
  // Cycling thoughts for the thinking indicator
  const thoughts = [
    "Analyzing request parameters...",
    "Identifying optimization opportunities...",
    "Gathering relevant data...",
    "Processing workload patterns...",
    "Evaluating cost implications...",
    "Formulating recommendations...",
    "Synthesizing insights...",
    "Preparing final analysis..."
  ];

  // Update elapsed time
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setElapsedTime(prev => prev + 100);
      }, 100);
      return () => clearInterval(interval);
    } else {
      setElapsedTime(0);
    }
  }, [isProcessing]);

  // Cycle through thoughts
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        setThoughtCycle(prev => (prev + 1) % thoughts.length);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isProcessing, thoughts.length]);

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const getStatusColor = () => {
    if (!subAgentStatus) return 'bg-gray-100';
    const lifecycle = typeof subAgentStatus === 'string' ? subAgentStatus : subAgentStatus.lifecycle;
    switch (lifecycle) {
      case 'running':
      case 'RUNNING': return 'bg-green-100 text-green-800';
      case 'completed':
      case 'COMPLETED': return 'bg-blue-100 text-blue-800';
      case 'failed':
      case 'FAILED': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = () => {
    if (!subAgentStatus) return <Bot className="w-4 h-4" />;
    const lifecycle = typeof subAgentStatus === 'string' ? subAgentStatus : subAgentStatus.lifecycle;
    switch (lifecycle) {
      case 'running':
      case 'RUNNING': return <Activity className="w-4 h-4 animate-pulse" />;
      case 'completed':
      case 'COMPLETED': return <TrendingUp className="w-4 h-4" />;
      case 'failed':
      case 'FAILED': return <Pause className="w-4 h-4" />;
      default: return <Bot className="w-4 h-4" />;
    }
  };

  return (
    <Card className="border-0 shadow-sm bg-gradient-to-r from-blue-50 via-white to-purple-50">
      <div className="p-4">
        {/* Main Header Row */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            {/* Agent Avatar */}
            <div className="relative">
              <div className={`w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center ${isProcessing ? 'animate-pulse' : ''}`}>
                <Bot className="w-6 h-6 text-white" />
              </div>
              {isProcessing && (
                <div className="absolute -bottom-1 -right-1">
                  <Sparkles className="w-4 h-4 text-yellow-500 animate-spin" />
                </div>
              )}
            </div>
            
            {/* Agent Name and Status */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                {metrics?.currentAgent || subAgentName}
                {isProcessing && (
                  <Badge variant="default" className="animate-pulse bg-blue-500 text-xs">
                    <Activity className="w-3 h-3 mr-1" />
                    Active
                  </Badge>
                )}
              </h2>
              {subAgentStatus && (
                <div className="flex items-center gap-2 mt-1">
                  <Badge className={`text-xs ${getStatusColor()}`}>
                    {getStatusIcon()}
                    <span className="ml-1">{typeof subAgentStatus === 'string' ? subAgentStatus : subAgentStatus.lifecycle}</span>
                  </Badge>
                  {/* Tools display commented out - SubAgentState doesn't have tools property
                  {subAgentStatus.tools && subAgentStatus.tools.length > 0 && (
                    <Badge variant="outline" className="text-xs">
                      <Zap className="w-3 h-3 mr-1" />
                      {subAgentStatus.tools.length} tools
                    </Badge>
                  )} */}
                </div>
              )}
            </div>
          </div>
          
          {/* Metrics Display */}
          <div className="flex items-center space-x-4">
            {metrics && (
              <>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Step</p>
                  <p className="text-sm font-semibold">{metrics.stepCount || 0}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Duration</p>
                  <p className="text-sm font-semibold">
                    {formatDuration(isProcessing ? elapsedTime : metrics.totalDuration)}
                  </p>
                </div>
              </>
            )}
            
            {/* Toggle Details Button */}
            {onToggleDetails && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleDetails}
                className="text-xs"
              >
                {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                {showDetails ? 'Less' : 'More'}
              </Button>
            )}
          </div>
        </div>

        {/* Thinking Indicator - Static bar with cycling thoughts */}
        {isProcessing && (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3"
            >
              {/* Progress Bar */}
              <div className="relative">
                <Progress value={60} className="h-1 bg-gray-200" />
                <div className="absolute top-0 left-0 h-1 bg-gradient-to-r from-blue-500 to-purple-500 animate-pulse" 
                     style={{ width: '60%' }} />
              </div>
              
              {/* Thought Display - Text cycles but bar stays static */}
              <div className="mt-2 flex items-center space-x-2">
                <Timer className="w-3 h-3 text-gray-400 animate-pulse" />
                <AnimatePresence mode="wait">
                  <motion.p
                    key={thoughtCycle}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ duration: 0.3 }}
                    className="text-xs text-gray-600 italic"
                  >
                    {thoughts[thoughtCycle]}
                  </motion.p>
                </AnimatePresence>
              </div>
            </motion.div>
          </AnimatePresence>
        )}

        {/* Expanded Details Section */}
        {showDetails && (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 pt-3 border-t border-gray-200"
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="flex items-center space-x-2">
                  <Layers className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500">Current Agent</p>
                    <p className="font-medium">{metrics?.currentAgent || subAgentName}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500">Total Time</p>
                    <p className="font-medium">{formatDuration(metrics?.totalDuration || elapsedTime)}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500">Steps Completed</p>
                    <p className="font-medium">{metrics?.stepCount || 0}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Settings className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-gray-500">Status</p>
                    <p className="font-medium">{subAgentStatus ? (typeof subAgentStatus === 'string' ? subAgentStatus : subAgentStatus.lifecycle) : 'idle'}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </Card>
  );
};