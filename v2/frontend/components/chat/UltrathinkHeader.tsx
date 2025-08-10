import React, { useEffect, useState, useMemo } from 'react';
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
  Settings, 
  Sparkles,
  Timer,
  TrendingUp,
  Zap,
  ChevronDown,
  ChevronUp,
  Brain,
  Cpu,
  CheckCircle,
  AlertCircle,
  FileText,
  ArrowRight
} from 'lucide-react';

interface UltrathinkStep {
  id: string;
  agent: string;
  thought: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  startTime?: number;
  endTime?: number;
  tools?: string[];
  details?: string;
}

interface UltrathinkHeaderProps {
  isThinking: boolean;
  currentStep?: UltrathinkStep;
  steps: UltrathinkStep[];
  onViewReport?: () => void;
  reportReady?: boolean;
}

export const UltrathinkHeader: React.FC<UltrathinkHeaderProps> = ({ 
  isThinking,
  currentStep,
  steps,
  onViewReport,
  reportReady = false
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime] = useState(Date.now());
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [showAllSteps, setShowAllSteps] = useState(false);
  const [thoughtCycle, setThoughtCycle] = useState(0);
  
  const cyclingThoughts = [
    "Analyzing request parameters...",
    "Identifying optimization opportunities...",
    "Gathering relevant data...",
    "Processing workload patterns...",
    "Evaluating cost implications...",
    "Formulating recommendations...",
    "Synthesizing insights...",
    "Preparing final analysis..."
  ];

  useEffect(() => {
    if (isThinking) {
      const interval = setInterval(() => {
        setElapsedTime(Date.now() - startTime);
      }, 100);
      return () => clearInterval(interval);
    }
  }, [isThinking, startTime]);

  useEffect(() => {
    if (isThinking && !currentStep) {
      const interval = setInterval(() => {
        setThoughtCycle(prev => (prev + 1) % cyclingThoughts.length);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isThinking, currentStep, cyclingThoughts.length]);

  const formatDuration = (ms: number) => {
    if (!ms) return '0s';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const getStepDuration = (step: UltrathinkStep) => {
    if (!step.startTime) return null;
    if (step.endTime) return step.endTime - step.startTime;
    if (step.status === 'active') return Date.now() - step.startTime;
    return null;
  };

  const totalDuration = useMemo(() => {
    const completedSteps = steps.filter(s => s.endTime);
    if (completedSteps.length === 0) return elapsedTime;
    const lastStep = completedSteps[completedSteps.length - 1];
    const firstStep = steps[0];
    if (firstStep.startTime && lastStep.endTime) {
      return lastStep.endTime - firstStep.startTime;
    }
    return elapsedTime;
  }, [steps, elapsedTime]);

  const getAgentIcon = (agent: string) => {
    if (agent.toLowerCase().includes('data')) return <Cpu className="w-4 h-4" />;
    if (agent.toLowerCase().includes('optim')) return <TrendingUp className="w-4 h-4" />;
    if (agent.toLowerCase().includes('analyz')) return <Brain className="w-4 h-4" />;
    return <Bot className="w-4 h-4" />;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'active': return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'error': return <AlertCircle className="w-4 h-4 text-red-500" />;
      default: return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const toggleStepExpanded = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  };

  return (
    <Card className="border-0 shadow-lg bg-gradient-to-r from-blue-50 via-white to-purple-50">
      <div className="p-6">
        {/* Main Header Row */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            {/* Agent Avatar with Animation */}
            <motion.div 
              className="relative"
              animate={isThinking ? { scale: [1, 1.05, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div className={`w-12 h-12 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center`}>
                <Bot className="w-7 h-7 text-white" />
              </div>
              {isThinking && (
                <motion.div 
                  className="absolute -bottom-1 -right-1"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Sparkles className="w-5 h-5 text-yellow-500" />
                </motion.div>
              )}
            </motion.div>
            
            {/* Agent Info */}
            <div>
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                Netra AI Optimizer
                {isThinking && (
                  <Badge variant="default" className="animate-pulse bg-gradient-to-r from-blue-500 to-purple-500 text-xs">
                    <Activity className="w-3 h-3 mr-1" />
                    Ultrathinking
                  </Badge>
                )}
              </h2>
              {currentStep && (
                <motion.p 
                  key={currentStep.id}
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-sm text-gray-600 flex items-center gap-2 mt-1"
                >
                  {getAgentIcon(currentStep.agent)}
                  <span className="font-medium">{currentStep.agent}</span>
                  <ArrowRight className="w-3 h-3" />
                  <span className="italic">{currentStep.thought}</span>
                </motion.p>
              )}
            </div>
          </div>
          
          {/* Metrics and Actions */}
          <div className="flex items-center space-x-6">
            {/* Live Metrics */}
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-xs text-gray-500">Total Time</p>
                <p className="text-lg font-bold text-gray-900">
                  {formatDuration(totalDuration)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Steps</p>
                <p className="text-lg font-bold text-gray-900">
                  {steps.filter(s => s.status === 'completed').length}/{steps.length}
                </p>
              </div>
            </div>
            
            {/* Report Button */}
            {reportReady && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              >
                <Button
                  onClick={onViewReport}
                  className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  View Report
                </Button>
              </motion.div>
            )}
            
            {/* Expand/Collapse */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAllSteps(!showAllSteps)}
            >
              {showAllSteps ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {showAllSteps ? 'Hide' : 'Show'} Details
            </Button>
          </div>
        </div>

        {/* Static Progress Bar with Animated Overlay */}
        {isThinking && (
          <div className="mb-4">
            <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
              <motion.div
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500"
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                style={{ width: '50%' }}
              />
              <div 
                className="absolute top-0 left-0 h-full bg-blue-300 opacity-30"
                style={{ width: `${(steps.filter(s => s.status === 'completed').length / steps.length) * 100}%` }}
              />
            </div>
            
            {/* Cycling Thought Display (when no current step) */}
            {!currentStep && (
              <motion.div className="mt-2 flex items-center space-x-2">
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
                    {cyclingThoughts[thoughtCycle]}
                  </motion.p>
                </AnimatePresence>
              </motion.div>
            )}
          </div>
        )}

        {/* Expandable Step Details */}
        <AnimatePresence>
          {showAllSteps && steps.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 pt-4 border-t border-gray-200"
            >
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {steps.map((step, idx) => {
                  const duration = getStepDuration(step);
                  const isExpanded = expandedSteps.has(step.id);
                  
                  return (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`p-3 rounded-lg border transition-all ${
                        step.status === 'active' 
                          ? 'border-blue-300 bg-blue-50' 
                          : step.status === 'completed'
                          ? 'border-green-200 bg-green-50'
                          : step.status === 'error'
                          ? 'border-red-200 bg-red-50'
                          : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <div 
                        className="flex items-center justify-between cursor-pointer"
                        onClick={() => toggleStepExpanded(step.id)}
                      >
                        <div className="flex items-center space-x-3">
                          {getStatusIcon(step.status)}
                          <div className="flex items-center space-x-2">
                            {getAgentIcon(step.agent)}
                            <span className="font-medium text-sm">{step.agent}</span>
                          </div>
                          <span className="text-sm text-gray-600">{step.thought}</span>
                        </div>
                        <div className="flex items-center space-x-3">
                          {duration && (
                            <Badge variant="outline" className="text-xs">
                              <Clock className="w-3 h-3 mr-1" />
                              {formatDuration(duration)}
                            </Badge>
                          )}
                          {step.tools && step.tools.length > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              <Zap className="w-3 h-3 mr-1" />
                              {step.tools.length} tools
                            </Badge>
                          )}
                          {step.details && (
                            <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                          )}
                        </div>
                      </div>
                      
                      {/* Expandable Details */}
                      <AnimatePresence>
                        {isExpanded && step.details && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-3 pt-3 border-t border-gray-200"
                          >
                            <p className="text-xs text-gray-600 whitespace-pre-wrap">{step.details}</p>
                            {step.tools && step.tools.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-1">
                                {step.tools.map((tool, toolIdx) => (
                                  <Badge key={toolIdx} variant="outline" className="text-xs">
                                    {tool}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
};