/**
 * Example Message Flow Component for DEV MODE
 * 
 * Provides example messages that users can select and send via WebSocket.
 * Includes real-time status updates and error handling.
 * 
 * Business Value: Demonstrates AI optimization capabilities to drive Free -> Paid conversion
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Send, CheckCircle, AlertCircle, Clock, Sparkles } from 'lucide-react';
import { webSocketService } from '@/services/webSocketService';
import { useAuthState } from '@/hooks/useAuthState';
import { logger } from '@/lib/logger';

// Example messages categorized by complexity and business value
export interface ExampleMessage {
  id: string;
  title: string;
  content: string;
  category: 'cost-optimization' | 'latency-optimization' | 'model-selection' | 'scaling' | 'advanced';
  complexity: 'basic' | 'intermediate' | 'advanced';
  estimatedTime: string;
  businessValue: 'conversion' | 'retention' | 'expansion';
}

const EXAMPLE_MESSAGES: ExampleMessage[] = [
  {
    id: 'cost-basic-1',
    title: 'Basic Cost Optimization',
    content: "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    category: 'cost-optimization',
    complexity: 'basic',
    estimatedTime: '30-60s',
    businessValue: 'conversion'
  },
  {
    id: 'latency-advanced-1',
    title: 'Advanced Latency Optimization',
    content: "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    category: 'latency-optimization',
    complexity: 'intermediate',
    estimatedTime: '60-90s',
    businessValue: 'retention'
  },
  {
    id: 'scaling-advanced-1',
    title: 'Usage Scaling Analysis',
    content: "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    category: 'scaling',
    complexity: 'advanced',
    estimatedTime: '90-120s',
    businessValue: 'expansion'
  },
  {
    id: 'model-selection-1',
    title: 'Model Selection Strategy',
    content: "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    category: 'model-selection',
    complexity: 'intermediate',
    estimatedTime: '45-75s',
    businessValue: 'retention'
  },
  {
    id: 'advanced-optimization-1',
    title: 'Multi-dimensional Optimization',
    content: "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
    category: 'advanced',
    complexity: 'advanced',
    estimatedTime: '120-180s',
    businessValue: 'expansion'
  }
];

interface ExampleMessageStatus {
  messageId: string;
  status: 'idle' | 'sending' | 'processing' | 'completed' | 'error';
  error?: string;
  startTime?: number;
  endTime?: number;
  agentUpdates?: string[];
}

interface MessageResult {
  output?: string;
  data?: Record<string, unknown>;
  recommendations?: string[];
  optimizations?: Record<string, unknown>;
}

interface ExampleMessageFlowProps {
  onMessageSent?: (message: ExampleMessage) => void;
  onMessageComplete?: (messageId: string, result: MessageResult) => void;
  onMessageError?: (messageId: string, error: string) => void;
}

export const ExampleMessageFlow: React.FC<ExampleMessageFlowProps> = ({
  onMessageSent,
  onMessageComplete,
  onMessageError
}) => {
  const [messageStatuses, setMessageStatuses] = useState<Map<string, ExampleMessageStatus>>(new Map());
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const { user } = useAuthState();

  // Initialize WebSocket message handling
  useEffect(() => {
    const handleWebSocketMessage = (message: { type: string; payload?: Record<string, unknown> }) => {
      logger.debug('Example Message Flow - WebSocket message received', { message });

      // Handle agent updates for example messages
      if (message.type === 'agent_started' || message.type === 'agent_thinking' || 
          message.type === 'tool_executing' || message.type === 'partial_result') {
        const messageId = message.payload?.example_message_id;
        if (messageId) {
          setMessageStatuses(prev => {
            const updated = new Map(prev);
            const current = updated.get(messageId) || { messageId, status: 'processing' };
            const agentUpdates = current.agentUpdates || [];
            agentUpdates.push(`${message.type}: ${message.payload?.content || 'Processing...'}`);
            updated.set(messageId, { ...current, agentUpdates, status: 'processing' });
            return updated;
          });
        }
      }

      // Handle completion
      if (message.type === 'agent_completed' || message.type === 'final_report') {
        const messageId = message.payload?.example_message_id;
        if (messageId) {
          setMessageStatuses(prev => {
            const updated = new Map(prev);
            const current = updated.get(messageId);
            if (current) {
              updated.set(messageId, { 
                ...current, 
                status: 'completed', 
                endTime: Date.now() 
              });
              onMessageComplete?.(messageId, message.payload);
            }
            return updated;
          });
        }
      }

      // Handle errors
      if (message.type === 'error') {
        const messageId = message.payload?.example_message_id;
        if (messageId) {
          const errorMsg = message.payload?.error || 'Unknown error occurred';
          setMessageStatuses(prev => {
            const updated = new Map(prev);
            const current = updated.get(messageId);
            if (current) {
              updated.set(messageId, { 
                ...current, 
                status: 'error', 
                error: errorMsg,
                endTime: Date.now() 
              });
              onMessageError?.(messageId, errorMsg);
            }
            return updated;
          });
        }
      }
    };

    webSocketService.onMessage = handleWebSocketMessage;

    return () => {
      webSocketService.onMessage = null;
    };
  }, [onMessageComplete, onMessageError]);

  const sendExampleMessage = useCallback(async (message: ExampleMessage) => {
    if (!user) {
      logger.warn('Cannot send message: User not authenticated');
      return;
    }

    logger.info('Sending example message', { messageId: message.id, title: message.title });

    // Update status to sending
    setMessageStatuses(prev => {
      const updated = new Map(prev);
      updated.set(message.id, {
        messageId: message.id,
        status: 'sending',
        startTime: Date.now()
      });
      return updated;
    });

    try {
      // Send message via WebSocket with example message metadata
      const websocketMessage = {
        type: 'chat_message',
        payload: {
          content: message.content,
          example_message_id: message.id,
          example_message_metadata: {
            title: message.title,
            category: message.category,
            complexity: message.complexity,
            businessValue: message.businessValue,
            estimatedTime: message.estimatedTime
          },
          timestamp: Date.now(),
          user_id: user.id
        }
      };

      webSocketService.send(websocketMessage);

      // Update status to processing
      setMessageStatuses(prev => {
        const updated = new Map(prev);
        const current = updated.get(message.id);
        if (current) {
          updated.set(message.id, { ...current, status: 'processing' });
        }
        return updated;
      });

      onMessageSent?.(message);

    } catch (error) {
      logger.error('Failed to send example message', error as Error, {
        messageId: message.id,
        userId: user.id
      });

      // Update status to error
      setMessageStatuses(prev => {
        const updated = new Map(prev);
        updated.set(message.id, {
          messageId: message.id,
          status: 'error',
          error: 'Failed to send message',
          endTime: Date.now()
        });
        return updated;
      });

      onMessageError?.(message.id, 'Failed to send message');
    }
  }, [user, onMessageSent, onMessageError]);

  const getStatusIcon = (status: ExampleMessageStatus['status']) => {
    switch (status) {
      case 'sending':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: ExampleMessageStatus['status']) => {
    const baseClasses = "text-xs";
    switch (status) {
      case 'sending':
        return <Badge variant="secondary" className={baseClasses}>Sending</Badge>;
      case 'processing':
        return <Badge variant="default" className={baseClasses}>Processing</Badge>;
      case 'completed':
        return <Badge variant="default" className={`${baseClasses} bg-green-100 text-green-800`}>Completed</Badge>;
      case 'error':
        return <Badge variant="destructive" className={baseClasses}>Error</Badge>;
      default:
        return <Badge variant="outline" className={baseClasses}>Ready</Badge>;
    }
  };

  const getCategoryColor = (category: ExampleMessage['category']) => {
    switch (category) {
      case 'cost-optimization':
        return 'bg-green-100 text-green-800';
      case 'latency-optimization':
        return 'bg-blue-100 text-blue-800';
      case 'model-selection':
        return 'bg-purple-100 text-purple-800';
      case 'scaling':
        return 'bg-orange-100 text-orange-800';
      case 'advanced':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredMessages = EXAMPLE_MESSAGES.filter(
    msg => selectedCategory === 'all' || msg.category === selectedCategory
  );

  const categories = ['all', ...Array.from(new Set(EXAMPLE_MESSAGES.map(m => m.category)))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-purple-500" />
        <h2 className="text-xl font-semibold">Example AI Optimization Messages</h2>
        <Badge variant="secondary" className="text-xs">DEV MODE</Badge>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map(category => (
          <Button
            key={category}
            variant={selectedCategory === category ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(category)}
          >
            {category.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </Button>
        ))}
      </div>

      {/* Authentication Check */}
      {!user && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please authenticate to send example messages
          </AlertDescription>
        </Alert>
      )}

      {/* Example Messages Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredMessages.map(message => {
          const status = messageStatuses.get(message.id);
          const isProcessing = status?.status === 'sending' || status?.status === 'processing';
          
          return (
            <Card key={message.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-sm font-medium">{message.title}</CardTitle>
                    <CardDescription className="text-xs mt-1">
                      {message.estimatedTime} • {message.complexity}
                    </CardDescription>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {getStatusIcon(status?.status || 'idle')}
                    {getStatusBadge(status?.status || 'idle')}
                  </div>
                </div>
                <div className="flex gap-1 mt-2">
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${getCategoryColor(message.category)}`}
                  >
                    {message.category.replace('-', ' ')}
                  </Badge>
                </div>
              </CardHeader>
              
              <CardContent className="pt-0">
                <p className="text-sm text-gray-600 mb-3 line-clamp-3">
                  {message.content}
                </p>

                {/* Status Updates */}
                {status?.agentUpdates && status.agentUpdates.length > 0 && (
                  <div className="mb-3 p-2 bg-gray-50 rounded text-xs">
                    <div className="font-medium mb-1">Agent Updates:</div>
                    {status.agentUpdates.slice(-2).map((update, idx) => (
                      <div key={idx} className="text-gray-600">
                        {update}
                      </div>
                    ))}
                  </div>
                )}

                {/* Error Display */}
                {status?.error && (
                  <Alert className="mb-3">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      {status.error}
                    </AlertDescription>
                  </Alert>
                )}

                {/* Timing Info */}
                {status?.startTime && status?.endTime && (
                  <div className="text-xs text-gray-500 mb-3">
                    Processing time: {((status.endTime - status.startTime) / 1000).toFixed(1)}s
                  </div>
                )}

                <Button
                  onClick={() => sendExampleMessage(message)}
                  disabled={!user || isProcessing}
                  size="sm"
                  className="w-full"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      {status?.status === 'sending' ? 'Sending...' : 'Processing...'}
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Try This Example
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">
            {Array.from(messageStatuses.values()).filter(s => s.status === 'completed').length}
          </div>
          <div className="text-xs text-gray-600">Completed</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-yellow-600">
            {Array.from(messageStatuses.values()).filter(s => s.status === 'processing').length}
          </div>
          <div className="text-xs text-gray-600">Processing</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">
            {Array.from(messageStatuses.values()).filter(s => s.status === 'error').length}
          </div>
          <div className="text-xs text-gray-600">Errors</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">
            {EXAMPLE_MESSAGES.length}
          </div>
          <div className="text-xs text-gray-600">Total Examples</div>
        </div>
      </div>
    </div>
  );
};

export default ExampleMessageFlow;