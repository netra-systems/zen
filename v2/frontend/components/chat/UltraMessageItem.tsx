"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  User,
  Bot,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Activity,
  AlertCircle,
  Eye,
  EyeOff,
  Download,
  Share2,
  ThumbsUp,
  ThumbsDown,
  Code,
  Terminal,
  Cpu,
  Timer,
  Zap,
  Database,
  Wrench,
  Target,
  FileText,
  TrendingUp,
  DollarSign,
  AlertTriangle
} from 'lucide-react';

interface UltraMessageProps {
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
    metrics?: {
      tokens_used?: number;
      api_calls?: number;
      cpu_usage?: number;
      memory_usage?: number;
      latency?: number;
    };
    insights?: Array<{
      type: 'optimization' | 'cost-saving' | 'warning';
      title: string;
      description: string;
      impact?: string;
      action?: string;
    }>;
  };
  isCurrentAgent?: boolean;
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

const agentColors: Record<string, string> = {
  'TriageSubAgent': 'from-blue-500 to-cyan-500',
  'DataSubAgent': 'from-purple-500 to-pink-500',
  'OptimizationsCoreSubAgent': 'from-amber-500 to-orange-500',
  'ActionsToMeetGoalsSubAgent': 'from-green-500 to-emerald-500',
  'ReportingSubAgent': 'from-indigo-500 to-purple-500',
  'Supervisor': 'from-gray-500 to-slate-500'
};

export const UltraMessageItem: React.FC<UltraMessageProps> = ({ 
  message, 
  isCurrentAgent = false 
}) => {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [helpfulness, setHelpfulness] = useState<'helpful' | 'not-helpful' | null>(null);
  const _codeBlockRef = useRef<HTMLDivElement>(null);

  // Real-time elapsed timer
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

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const AgentIcon = agentIcons[message.sub_agent_name || 'Default'] || Bot;
  const gradientColor = agentColors[message.sub_agent_name || 'Default'] || 'from-gray-500 to-slate-500';

  const isUser = message.type === 'user';
  const isError = message.type === 'error';
  const isAI = message.type === 'agent';

  // Render agent transition banner
  if (message.agent_transition) {
    return (
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="my-4 px-6"
      >
        <div className={cn(
          "relative overflow-hidden rounded-xl p-4",
          "bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-cyan-500/10",
          "border border-purple-500/20"
        )}>
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-purple-500/20 via-transparent to-cyan-500/20"
            animate={{ x: ['0%', '100%', '0%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-purple-500" />
              <span className="text-sm font-medium">
                Transitioning from <span className="font-semibold text-purple-600">{message.agent_transition.from}</span> to{' '}
                <span className="font-semibold text-blue-600">{message.agent_transition.to}</span>
              </span>
            </div>
            <span className="text-xs text-gray-500">
              {new Date(message.agent_transition.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "mb-4 px-6",
        isUser && "flex justify-end"
      )}
    >
      <div className={cn(
        "relative max-w-4xl",
        isUser ? "ml-12" : "mr-12"
      )}>
        {/* Message Card */}
        <Card className={cn(
          "overflow-hidden transition-all duration-200 hover:shadow-lg",
          isUser && "bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200",
          isError && "bg-gradient-to-br from-red-50 to-rose-50 border-red-200",
          isAI && "bg-white border-gray-200",
          isCurrentAgent && "ring-2 ring-purple-500 ring-opacity-50"
        )}>
          {/* Header */}
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {/* Avatar */}
                <Avatar className={cn(
                  "w-10 h-10",
                  isCurrentAgent && "ring-2 ring-purple-500 ring-offset-2"
                )}>
                  <AvatarFallback className={cn(
                    "text-white font-semibold",
                    isUser ? "bg-gradient-to-br from-blue-500 to-blue-600" :
                    isError ? "bg-gradient-to-br from-red-500 to-red-600" :
                    `bg-gradient-to-br ${gradientColor}`
                  )}>
                    {isUser ? <User className="w-5 h-5" /> : 
                     isError ? <AlertCircle className="w-5 h-5" /> :
                     <AgentIcon className="w-5 h-5" />}
                  </AvatarFallback>
                </Avatar>

                {/* Name and Status */}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">
                      {isUser ? 'You' : 
                       isError ? 'System Error' :
                       message.sub_agent_name || 'Netra AI'}
                    </span>
                    {isCurrentAgent && (
                      <motion.div
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <Badge variant="outline" className="text-xs border-purple-500 text-purple-600">
                          <Activity className="w-3 h-3 mr-1" />
                          Processing
                        </Badge>
                      </motion.div>
                    )}
                    {message.step_number && message.total_steps && (
                      <Badge variant="secondary" className="text-xs">
                        Step {message.step_number}/{message.total_steps}
                      </Badge>
                    )}
                  </div>
                  
                  {/* Timing */}
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-500">
                      {new Date(message.created_at || Date.now()).toLocaleTimeString()}
                    </span>
                    {(message.step_timing?.duration || elapsedTime > 0) && (
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Timer className="w-3 h-3" />
                        <span>{formatDuration(message.step_timing?.duration || elapsedTime)}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8"
                  onClick={() => setShowDetails(!showDetails)}
                >
                  {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-8 h-8"
                  onClick={() => handleCopy(message.content || '')}
                >
                  {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                </Button>
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

            {/* Tool Info Badges */}
            {message.tool_info && Array.isArray(message.tool_info) && (
              <div className="flex flex-wrap gap-1 mt-2">
                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                {(message.tool_info as any[]).map((tool: any, idx: number) => (
                  <Badge key={idx} variant="outline" className="text-xs">
                    <Wrench className="w-3 h-3 mr-1" />
                    {tool.tool_name}
                    {tool.status && (
                      <span className={cn(
                        "ml-1 w-2 h-2 rounded-full",
                        tool.status === 'completed' && "bg-green-500",
                        tool.status === 'running' && "bg-blue-500 animate-pulse",
                        tool.status === 'failed' && "bg-red-500"
                      )} />
                    )}
                  </Badge>
                ))}
              </div>
            )}
          </CardHeader>

          {/* Content */}
          <CardContent className="pt-2">
            {/* Main Content with Markdown */}
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                    code(props: any) {
                    const { className, children } = props;
                    const inline = props.inline as boolean | undefined;
                    const match = /language-(\w+)/.exec(className || '');
                    const language = match ? match[1] : 'text';
                    
                    if (inline) {
                      return (
                        <code className="px-1 py-0.5 rounded bg-gray-100 text-sm font-mono" {...props}>
                          {children}
                        </code>
                      );
                    }
                    
                    return (
                      <div className="relative my-2">
                        <div className="flex items-center justify-between bg-gray-800 px-3 py-2 rounded-t-lg">
                          <span className="text-xs text-gray-400">{language}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-gray-400 hover:text-white"
                            onClick={() => handleCopy(String(children).replace(/\n$/, ''))}
                          >
                            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                            <span className="ml-1 text-xs">Copy</span>
                          </Button>
                        </div>
                        <SyntaxHighlighter
                          language={language}
                          style={oneDark}
                          customStyle={{
                            margin: 0,
                            borderTopLeftRadius: 0,
                            borderTopRightRadius: 0,
                          }}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      </div>
                    );
                  },
                }}
              >
                {message.content || ''}
              </ReactMarkdown>
            </div>

            {/* Insights Cards */}
            {message.insights && message.insights.length > 0 && (
              <div className="mt-4 space-y-2">
                {message.insights.map((insight, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={cn(
                      "p-3 rounded-lg border",
                      insight.type === 'optimization' && "bg-purple-50 border-purple-200",
                      insight.type === 'cost-saving' && "bg-green-50 border-green-200",
                      insight.type === 'warning' && "bg-amber-50 border-amber-200"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className={cn(
                        "p-2 rounded-lg",
                        insight.type === 'optimization' && "bg-purple-100",
                        insight.type === 'cost-saving' && "bg-green-100",
                        insight.type === 'warning' && "bg-amber-100"
                      )}>
                        {insight.type === 'optimization' && <Sparkles className="w-4 h-4 text-purple-600" />}
                        {insight.type === 'cost-saving' && <DollarSign className="w-4 h-4 text-green-600" />}
                        {insight.type === 'warning' && <AlertTriangle className="w-4 h-4 text-amber-600" />}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm">{insight.title}</h4>
                        <p className="text-xs text-gray-600 mt-1">{insight.description}</p>
                        {insight.impact && (
                          <div className="flex items-center gap-1 mt-2">
                            <TrendingUp className="w-3 h-3 text-gray-500" />
                            <span className="text-xs text-gray-500">Impact: {insight.impact}</span>
                          </div>
                        )}
                        {insight.action && (
                          <Button variant="outline" size="sm" className="mt-2 h-7 text-xs">
                            {insight.action}
                          </Button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {/* Expanded Details */}
            <AnimatePresence>
              {(isExpanded || showDetails) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-4 pt-4 border-t"
                >
                  {/* Metrics Dashboard */}
                  {message.metrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                      {message.metrics.tokens_used && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                            <Code className="w-3 h-3" />
                            <span>Tokens</span>
                          </div>
                          <div className="text-lg font-semibold">{message.metrics.tokens_used.toLocaleString()}</div>
                        </div>
                      )}
                      {message.metrics.api_calls && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                            <Terminal className="w-3 h-3" />
                            <span>API Calls</span>
                          </div>
                          <div className="text-lg font-semibold">{message.metrics.api_calls}</div>
                        </div>
                      )}
                      {message.metrics.latency && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                            <Zap className="w-3 h-3" />
                            <span>Latency</span>
                          </div>
                          <div className="text-lg font-semibold">{message.metrics.latency}ms</div>
                        </div>
                      )}
                      {message.metrics.cpu_usage && (
                        <div className="bg-gray-50 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
                            <Cpu className="w-3 h-3" />
                            <span>CPU Usage</span>
                          </div>
                          <div className="text-lg font-semibold">{message.metrics.cpu_usage}%</div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Raw Data */}
                  {message.raw_data && (
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-600">Raw Data</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2"
                          onClick={() => handleCopy(JSON.stringify(message.raw_data, null, 2))}
                        >
                          <Copy className="w-3 h-3" />
                        </Button>
                      </div>
                      <pre className="text-xs overflow-x-auto">
                        <code>{JSON.stringify(message.raw_data, null, 2)}</code>
                      </pre>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Feedback Section */}
            {isAI && !isCurrentAgent && (
              <div className="flex items-center gap-2 mt-4 pt-4 border-t">
                <span className="text-xs text-gray-500">Was this helpful?</span>
                <Button
                  variant={helpfulness === 'helpful' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setHelpfulness('helpful')}
                >
                  <ThumbsUp className="w-3 h-3" />
                </Button>
                <Button
                  variant={helpfulness === 'not-helpful' ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setHelpfulness('not-helpful')}
                >
                  <ThumbsDown className="w-3 h-3" />
                </Button>
                <div className="flex-1" />
                <Button variant="ghost" size="sm" className="h-7 px-2">
                  <Share2 className="w-3 h-3 mr-1" />
                  <span className="text-xs">Share</span>
                </Button>
                <Button variant="ghost" size="sm" className="h-7 px-2">
                  <Download className="w-3 h-3 mr-1" />
                  <span className="text-xs">Export</span>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Processing Indicator Line */}
        {isCurrentAgent && (
          <motion.div
            className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-purple-500 rounded-b-lg"
            animate={{ x: ['0%', '100%', '0%'] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
        )}
      </div>
    </motion.div>
  );
};