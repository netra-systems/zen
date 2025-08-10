import React, { useState, useEffect } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Progress } from '@/components/ui/progress';
import { RawJsonView } from './RawJsonView';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertCircle, 
  Bot, 
  ChevronDown, 
  ChevronRight, 
  Clock, 
  Code, 
  FileText, 
  User, 
  Wrench,
  Activity,
  Sparkles,
  Timer,
  Layers,
  Eye,
  EyeOff
} from 'lucide-react';

interface EnhancedMessageProps {
  message: MessageType & {
    agent_transition?: {
      from: string;
      to: string;
      timestamp: string;
    };
    step_timing?: {
      start: string;
      end?: string;
      duration?: number;
    };
    step_number?: number;
    total_steps?: number;
  };
  isCurrentAgent?: boolean;
  showDetailedMetrics?: boolean;
}

export const EnhancedMessageItem: React.FC<EnhancedMessageProps> = ({ 
  message, 
  isCurrentAgent = false,
  showDetailedMetrics = false
}) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references, error, created_at, id } = message;
  const [isToolExpanded, setIsToolExpanded] = useState(false);
  const [isRawExpanded, setIsRawExpanded] = useState(false);
  const [isDetailsExpanded, setIsDetailsExpanded] = useState(false);
  const [elapsedTime, setElapsedTime] = useState<number>(0);

  // Real-time elapsed time for current processing
  useEffect(() => {
    if (isCurrentAgent && message.step_timing?.start && !message.step_timing?.end) {
      const interval = setInterval(() => {
        const start = new Date(message.step_timing!.start).getTime();
        const now = Date.now();
        setElapsedTime(now - start);
      }, 100);
      
      return () => clearInterval(interval);
    }
  }, [isCurrentAgent, message.step_timing]);

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return new Date().toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
    
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 1
    });
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${((ms % 60000) / 1000).toFixed(1)}s`;
  };

  const getMessageIcon = () => {
    switch (type) {
      case 'user':
        return <User className="w-4 h-4" />;
      case 'tool':
        return <Wrench className="w-4 h-4" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Bot className="w-4 h-4" />;
    }
  };

  const getAgentStatusColor = () => {
    if (error) return 'bg-red-100 border-red-300';
    if (isCurrentAgent) return 'bg-blue-100 border-blue-300 animate-pulse';
    if (type === 'tool') return 'bg-purple-100 border-purple-300';
    if (type === 'user') return 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200';
    return 'bg-white border-gray-200';
  };

  const renderContent = () => {
    if (error) {
      return (
        <div className="flex items-start space-x-2 p-3 bg-red-50 rounded-lg border border-red-200">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      );
    }
    
    if (tool_info) {
      return (
        <div className="space-y-3">
          <Collapsible open={isToolExpanded} onOpenChange={setIsToolExpanded}>
            <CollapsibleTrigger className="flex items-center space-x-2 text-purple-600 hover:text-purple-700 font-medium text-sm">
              {isToolExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <Code className="w-4 h-4" />
              <span>Tool: {tool_info.tool_name || 'Unknown'}</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-3">
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <RawJsonView data={tool_info} />
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      );
    }
    
    return (
      <div className="space-y-3">
        <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{content}</p>
        
        {type === 'user' && references && references.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="font-semibold text-sm text-blue-800">References</span>
            </div>
            <ul className="space-y-1">
              {references.map((ref, index) => (
                <li key={`${id}-ref-${index}`} className="text-sm text-blue-700 flex items-start">
                  <span className="mr-2 text-blue-500">•</span>
                  <span>{ref}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`mb-4 flex ${type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <Card className={`w-full max-w-3xl shadow-sm hover:shadow-md transition-all duration-200 ${getAgentStatusColor()}`}>
        {/* Agent Transition Indicator */}
        {message.agent_transition && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-4 py-2 text-sm flex items-center gap-2">
            <Layers className="w-4 h-4" />
            <span>Agent transition: {message.agent_transition.from} → {message.agent_transition.to}</span>
          </motion.div>
        )}

        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <Avatar className="w-9 h-9 border-2 border-white shadow-sm">
                <AvatarFallback className={`font-bold text-sm ${
                  type === 'user' ? 'bg-blue-500 text-white' : 
                  isCurrentAgent ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white animate-pulse' :
                  'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                }`}>
                  {type === 'user' ? 'U' : 'AI'}
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center space-x-2">
                  {getMessageIcon()}
                  <CardTitle className="text-base font-semibold text-gray-900">
                    {sub_agent_name || (type === 'user' ? 'You' : 'Netra Agent')}
                  </CardTitle>
                  {isCurrentAgent && (
                    <Badge variant="default" className="animate-pulse bg-blue-500">
                      <Activity className="w-3 h-3 mr-1" />
                      Active
                    </Badge>
                  )}
                </div>
                {type !== 'user' && sub_agent_name && (
                  <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-gray-500">
                      {type === 'tool' ? 'Tool Execution' : 'Agent Response'}
                    </p>
                    {message.step_number && message.total_steps && (
                      <Badge variant="outline" className="text-xs">
                        Step {message.step_number} of {message.total_steps}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end space-y-1">
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <Clock className="w-3 h-3" />
                <span>{formatTimestamp(created_at)}</span>
              </div>
              {/* Step timing display */}
              {message.step_timing && (
                <div className="flex items-center space-x-2">
                  <Timer className="w-3 h-3 text-gray-400" />
                  <span className="text-xs text-gray-600">
                    {message.step_timing.end 
                      ? formatDuration(message.step_timing.duration || 0)
                      : formatDuration(elapsedTime)
                    }
                  </span>
                  {!message.step_timing.end && (
                    <Sparkles className="w-3 h-3 text-blue-500 animate-spin" />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Progress indicator for current processing */}
          {isCurrentAgent && !message.step_timing?.end && (
            <div className="mt-3">
              <Progress className="h-1" value={60} />
              <p className="text-xs text-gray-500 mt-1">Processing...</p>
            </div>
          )}
        </CardHeader>
        
        <CardContent className="px-5 pb-4">
          {renderContent()}
          
          {/* Expandable Details Section */}
          {showDetailedMetrics && (message.step_timing || raw_data) && (
            <Collapsible open={isDetailsExpanded} onOpenChange={setIsDetailsExpanded} className="mt-4">
              <CollapsibleTrigger className="flex items-center space-x-2 text-xs text-gray-500 hover:text-gray-700 transition-colors">
                {isDetailsExpanded ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                <span>Detailed Metrics</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200 space-y-2">
                  {message.step_timing && (
                    <div className="text-xs space-y-1">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Start:</span>
                        <span className="font-mono">{formatTimestamp(message.step_timing.start)}</span>
                      </div>
                      {message.step_timing.end && (
                        <div className="flex justify-between">
                          <span className="text-gray-600">End:</span>
                          <span className="font-mono">{formatTimestamp(message.step_timing.end)}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-gray-600">Duration:</span>
                        <span className="font-mono">
                          {message.step_timing.duration 
                            ? formatDuration(message.step_timing.duration)
                            : formatDuration(elapsedTime)
                          }
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
          
          {/* Raw data viewer */}
          {raw_data && (
            <Collapsible open={isRawExpanded} onOpenChange={setIsRawExpanded} className="mt-4">
              <CollapsibleTrigger className="flex items-center space-x-2 text-xs text-gray-500 hover:text-gray-700 transition-colors">
                {isRawExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                <Code className="w-3 h-3" />
                <span>Raw Data</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                  <RawJsonView data={raw_data} />
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
          
          {id && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400">Message ID: {id}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};