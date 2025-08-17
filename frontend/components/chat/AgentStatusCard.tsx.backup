"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  Bot,
  Activity,
  Zap,
  Clock,
  Cpu,
  HardDrive,
  Terminal,
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Target,
  Database,
  FileText,
  Sparkles
} from 'lucide-react';

interface AgentStatusCardProps {
  agentName: string;
  status: 'idle' | 'thinking' | 'executing' | 'success' | 'error' | 'cancelled';
  currentAction?: string;
  progress?: number;
  eta?: number;
  tools?: Array<{
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    duration?: number;
  }>;
  metrics?: {
    cpu?: number;
    memory?: number;
    apiCalls?: number;
    tokensUsed?: number;
  };
  logs?: string[];
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  isPaused?: boolean;
}

const agentIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  'TriageSubAgent': Target,
  'DataSubAgent': Database,
  'OptimizationsCoreSubAgent': Zap,
  'ActionsToMeetGoalsSubAgent': Terminal,
  'ReportingSubAgent': FileText,
  'Supervisor': Bot,
  'Default': Bot
};

const statusColors: Record<string, string> = {
  idle: 'bg-gray-100 text-gray-600',
  thinking: 'bg-blue-100 text-blue-600',
  executing: 'bg-purple-100 text-purple-600',
  success: 'bg-green-100 text-green-600',
  error: 'bg-red-100 text-red-600',
  cancelled: 'bg-orange-100 text-orange-600'
};

const statusAnimations: Record<string, { opacity?: number[], rotate?: number }> = {
  thinking: { opacity: [0.5, 1, 0.5] },
  executing: { rotate: 360 }
};

export const AgentStatusCard: React.FC<AgentStatusCardProps> = ({
  agentName,
  status,
  currentAction,
  progress = 0,
  eta,
  tools = [],
  metrics = {},
  logs = [],
  onCancel,
  onPause,
  onResume,
  isPaused = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showLogs, setShowLogs] = useState(false);
  const startTimeRef = React.useRef(Date.now());

  useEffect(() => {
    if (status === 'executing' || status === 'thinking') {
      const interval = setInterval(() => {
        setElapsedTime(Date.now() - startTimeRef.current);
      }, 1000);
      return () => clearInterval(interval);
    } else {
      startTimeRef.current = Date.now();
      setElapsedTime(0);
    }
  }, [status]);

  const formatTime = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const AgentIcon = agentIcons[agentName] || Bot;
  const statusColor = statusColors[status];
  const statusAnimation = statusAnimations[status];

  const getStatusIcon = () => {
    switch (status) {
      case 'idle': return <Clock className="w-4 h-4" />;
      case 'thinking': return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'executing': return <Activity className="w-4 h-4" />;
      case 'success': return <CheckCircle className="w-4 h-4" />;
      case 'error': return <AlertCircle className="w-4 h-4" />;
      case 'cancelled': return <X className="w-4 h-4" />;
      default: return <Bot className="w-4 h-4" />;
    }
  };

  return (
    <Card className={cn(
      "overflow-hidden transition-all duration-300",
      "hover:shadow-lg",
      status === 'executing' && "ring-2 ring-purple-500 ring-opacity-50",
      status === 'thinking' && "ring-2 ring-blue-500 ring-opacity-50",
      status === 'error' && "ring-2 ring-red-500 ring-opacity-50"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {/* Agent Avatar */}
            <motion.div
              animate={statusAnimation}
              transition={
                status === 'thinking' 
                  ? { duration: 2, repeat: Infinity }
                  : status === 'executing'
                  ? { duration: 3, repeat: Infinity, ease: "linear" }
                  : {}
              }
              className={cn(
                "p-3 rounded-xl",
                "bg-gradient-to-br",
                status === 'idle' && "from-gray-400 to-gray-500",
                status === 'thinking' && "from-blue-400 to-blue-600",
                status === 'executing' && "from-purple-400 to-purple-600",
                status === 'success' && "from-green-400 to-green-600",
                status === 'error' && "from-red-400 to-red-600",
                status === 'cancelled' && "from-orange-400 to-orange-600"
              )}
            >
              <AgentIcon className="w-6 h-6 text-white" />
            </motion.div>

            <div>
              <CardTitle className="text-lg font-semibold">{agentName}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge className={cn("text-xs", statusColor)}>
                  {getStatusIcon()}
                  <span className="ml-1 capitalize">{isPaused ? 'Paused' : status}</span>
                </Badge>
                {elapsedTime > 0 && (
                  <span className="text-xs text-gray-500">
                    {formatTime(elapsedTime)}
                  </span>
                )}
                {eta && (
                  <span className="text-xs text-gray-500">
                    ETA: {formatTime(eta)}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center gap-1">
            {(status === 'executing' || status === 'thinking') && (
              <>
                {isPaused ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-8 h-8"
                    onClick={onResume}
                  >
                    <Play className="w-4 h-4" />
                  </Button>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="w-8 h-8"
                    onClick={onPause}
                  >
                    <Pause className="w-4 h-4" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8 text-red-500 hover:text-red-600"
                  onClick={onCancel}
                >
                  <X className="w-4 h-4" />
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="w-8 h-8"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Current Action */}
        {currentAction && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 p-2 bg-gray-50 rounded-lg"
          >
            <p className="text-sm text-gray-600">{currentAction}</p>
          </motion.div>
        )}

        {/* Progress Bar */}
        {(status === 'executing' || status === 'thinking') && progress > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-500">Progress</span>
              <span className="text-xs font-medium">{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}
      </CardHeader>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <CardContent className="pt-0">
              {/* Tool Stack */}
              {tools.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold mb-2">Tool Execution</h4>
                  <div className="space-y-2">
                    {tools.map((tool, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-gray-500" />
                          <span className="text-sm">{tool.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {tool.duration && (
                            <span className="text-xs text-gray-500">
                              {formatTime(tool.duration)}
                            </span>
                          )}
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              tool.status === 'completed' && "border-green-500 text-green-600",
                              tool.status === 'running' && "border-blue-500 text-blue-600",
                              tool.status === 'failed' && "border-red-500 text-red-600",
                              tool.status === 'pending' && "border-gray-300 text-gray-500"
                            )}
                          >
                            {tool.status === 'running' && (
                              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                            )}
                            {tool.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resource Metrics */}
              {Object.keys(metrics).length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold mb-2">Resource Usage</h4>
                  <div className="grid grid-cols-2 gap-3">
                    {metrics.cpu !== undefined && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                          <Cpu className="w-3 h-3" />
                          <span>CPU Usage</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold">{metrics.cpu}%</div>
                          <div className="flex-1">
                            <Progress value={metrics.cpu} className="h-1" />
                          </div>
                        </div>
                      </div>
                    )}
                    {metrics.memory !== undefined && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                          <HardDrive className="w-3 h-3" />
                          <span>Memory</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold">{metrics.memory}%</div>
                          <div className="flex-1">
                            <Progress value={metrics.memory} className="h-1" />
                          </div>
                        </div>
                      </div>
                    )}
                    {metrics.apiCalls !== undefined && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                          <Zap className="w-3 h-3" />
                          <span>API Calls</span>
                        </div>
                        <div className="text-lg font-semibold">{metrics.apiCalls}</div>
                      </div>
                    )}
                    {metrics.tokensUsed !== undefined && (
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                          <Sparkles className="w-3 h-3" />
                          <span>Tokens</span>
                        </div>
                        <div className="text-lg font-semibold">{metrics.tokensUsed.toLocaleString()}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Execution Logs */}
              {logs.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold">Execution Logs</h4>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => setShowLogs(!showLogs)}
                    >
                      {showLogs ? 'Hide' : 'Show'}
                    </Button>
                  </div>
                  <AnimatePresence>
                    {showLogs && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto"
                      >
                        <pre className="text-xs text-gray-300 font-mono">
                          {logs.join('\n')}
                        </pre>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
};