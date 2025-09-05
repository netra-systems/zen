/**
 * UVS Chat Interface - Complete integration example
 * 
 * CRITICAL: Shows how to use all UVS components together for
 * multiturn conversation support with all report types.
 * 
 * Business Value: Reference implementation for UVS chat integration
 */

'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useUVSConversation, useMessageQueue, useWebSocketStatus } from '@/hooks/useUVSConversation';
import { UVSErrorBoundary } from './UVSErrorBoundary';
import { UVSReportDisplay, UVSReport } from './UVSReportDisplay';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Send, 
  Loader2, 
  Wifi, 
  WifiOff, 
  Trash2,
  XCircle,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { logger } from '@/lib/logger';

interface UVSChatInterfaceProps {
  userId: string;
  className?: string;
}

/**
 * Connection Status Indicator
 */
const ConnectionStatus: React.FC<{ 
  status: 'connecting' | 'connected' | 'disconnected' | 'error' 
}> = ({ status }) => {
  const config = {
    connecting: { icon: Loader2, color: 'text-yellow-600', text: 'Connecting...', animate: true },
    connected: { icon: Wifi, color: 'text-green-600', text: 'Connected', animate: false },
    disconnected: { icon: WifiOff, color: 'text-gray-600', text: 'Disconnected', animate: false },
    error: { icon: AlertCircle, color: 'text-red-600', text: 'Connection Error', animate: false }
  };
  
  const { icon: Icon, color, text, animate } = config[status];
  
  return (
    <div className={`flex items-center gap-2 ${color}`}>
      <Icon className={`w-4 h-4 ${animate ? 'animate-spin' : ''}`} />
      <span className="text-sm font-medium">{text}</span>
    </div>
  );
};

/**
 * Message Queue Indicator
 */
const QueueIndicator: React.FC<{ 
  queueLength: number; 
  isProcessing: boolean 
}> = ({ queueLength, isProcessing }) => {
  if (queueLength === 0 && !isProcessing) return null;
  
  return (
    <div className="flex items-center gap-2">
      {isProcessing && (
        <Badge variant="secondary" className="gap-1">
          <Loader2 className="w-3 h-3 animate-spin" />
          Processing
        </Badge>
      )}
      {queueLength > 0 && (
        <Badge variant="outline">
          {queueLength} queued
        </Badge>
      )}
    </div>
  );
};

/**
 * Message Display Component
 */
const MessageDisplay: React.FC<{ 
  message: any;
  isLatest: boolean;
}> = ({ message, isLatest }) => {
  const roleConfig = {
    user: { bg: 'bg-blue-50 dark:bg-blue-900/10', align: 'ml-auto' },
    assistant: { bg: 'bg-gray-50 dark:bg-gray-900/10', align: 'mr-auto' },
    system: { bg: 'bg-yellow-50 dark:bg-yellow-900/10', align: 'mx-auto' }
  };
  
  const config = roleConfig[message.role as keyof typeof roleConfig] || roleConfig.system;
  
  return (
    <div className={`max-w-[80%] ${config.align}`}>
      <div className={`p-3 rounded-lg ${config.bg} ${isLatest ? 'animate-fadeIn' : ''}`}>
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="outline" className="text-xs">
                {message.role}
              </Badge>
              {message.status === 'sending' && (
                <Loader2 className="w-3 h-3 animate-spin text-gray-500" />
              )}
              {message.status === 'failed' && (
                <XCircle className="w-3 h-3 text-red-500" />
              )}
              {message.status === 'sent' && (
                <CheckCircle className="w-3 h-3 text-green-500" />
              )}
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {message.text}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Main UVS Chat Interface Component
 */
export const UVSChatInterface: React.FC<UVSChatInterfaceProps> = ({ 
  userId, 
  className = '' 
}) => {
  const [inputValue, setInputValue] = useState('');
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  
  // Use the main UVS conversation hook
  const {
    messages,
    isProcessing,
    isConnected,
    currentReport,
    queueStatus,
    sendMessage,
    clearConversation,
    retryConnection,
    cancelCurrentMessage,
    connectionStatus,
    lastError
  } = useUVSConversation({
    userId,
    autoConnect: true,
    onError: (error) => {
      logger.error('🚨 UVS Chat Error', { error });
    },
    onReportReceived: (report) => {
      logger.info('UVS Report received', { reportType: report.report_type });
    }
  });
  
  /**
   * Handle send message
   */
  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isProcessing) return;
    
    const messageText = inputValue.trim();
    setInputValue('');
    
    try {
      await sendMessage(messageText);
    } catch (error) {
      logger.error('🚨 Failed to send message', { error });
      // Error is already handled by the hook
    }
  }, [inputValue, isProcessing, sendMessage]);
  
  /**
   * Handle question click from guidance report
   */
  const handleQuestionClick = useCallback((question: string) => {
    setInputValue(question);
    // Auto-send the question
    setTimeout(() => {
      handleSend();
    }, 100);
  }, [handleSend]);
  
  /**
   * Handle next step click
   */
  const handleNextStepClick = useCallback((step: string) => {
    logger.info('Next step clicked', { step });
    // Could implement specific actions based on the step
    setInputValue(step);
  }, []);
  
  /**
   * Auto-scroll to bottom when messages update
   */
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);
  
  return (
    <UVSErrorBoundary userId={userId}>
      <Card className={`flex flex-col h-[600px] ${className}`}>
        {/* Header */}
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <CardTitle>AI Optimization Assistant</CardTitle>
            <div className="flex items-center gap-4">
              <QueueIndicator 
                queueLength={queueStatus.queueLength} 
                isProcessing={queueStatus.isProcessing} 
              />
              <ConnectionStatus status={connectionStatus} />
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col p-0">
          {/* Error Alert */}
          {lastError && (
            <Alert className="m-4 mb-0" variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {lastError.message}
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="ml-2"
                  onClick={retryConnection}
                >
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          
          {/* Messages Area */}
          <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
            <div className="space-y-4">
              {/* Show messages */}
              {messages.map((message, index) => (
                <MessageDisplay 
                  key={message.id} 
                  message={message}
                  isLatest={index === messages.length - 1}
                />
              ))}
              
              {/* Show current report if available */}
              {currentReport && (
                <div className="my-6">
                  <UVSReportDisplay
                    report={currentReport}
                    onQuestionClick={handleQuestionClick}
                    onNextStepClick={handleNextStepClick}
                    onRetry={retryConnection}
                  />
                </div>
              )}
              
              {/* Processing indicator */}
              {isProcessing && !currentReport && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                  <span className="ml-2 text-sm text-gray-500">
                    AI is thinking...
                  </span>
                </div>
              )}
            </div>
          </ScrollArea>
          
          {/* Input Area */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder={
                  !isConnected 
                    ? "Connecting..." 
                    : "Ask about AI optimization..."
                }
                disabled={!isConnected || isProcessing}
                className="flex-1"
              />
              
              <Button
                onClick={handleSend}
                disabled={!isConnected || isProcessing || !inputValue.trim()}
                size="icon"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
              
              {isProcessing && (
                <Button
                  onClick={cancelCurrentMessage}
                  variant="outline"
                  size="icon"
                  title="Cancel current message"
                >
                  <XCircle className="w-4 h-4" />
                </Button>
              )}
              
              <Button
                onClick={clearConversation}
                variant="outline"
                size="icon"
                title="Clear conversation"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Helper text */}
            <p className="text-xs text-gray-500 mt-2">
              {!isConnected && "Establishing connection..."}
              {isConnected && messages.length === 0 && "Start by asking about your AI usage or optimization goals"}
              {isConnected && queueStatus.queueLength > 0 && `${queueStatus.queueLength} message(s) in queue`}
            </p>
          </div>
        </CardContent>
      </Card>
    </UVSErrorBoundary>
  );
};

// Export example usage
export const UVSChatExample: React.FC = () => {
  // In real app, get userId from auth context
  const userId = 'example-user-123';
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">UVS Multiturn Conversation Demo</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Main Chat */}
        <UVSChatInterface userId={userId} />
        
        {/* Info Panel */}
        <Card>
          <CardHeader>
            <CardTitle>About UVS</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              The Universal Value System (UVS) ensures you always get valuable 
              responses, even with no data or when errors occur.
            </p>
            
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Report Types:</h3>
              <ul className="text-sm space-y-1 ml-4">
                <li>✅ <strong>Full:</strong> Complete analysis with data and optimizations</li>
                <li>📊 <strong>Partial:</strong> Working with available information</li>
                <li>🎯 <strong>Guidance:</strong> Exploratory questions to understand needs</li>
                <li>🔄 <strong>Fallback:</strong> Alternative assistance when errors occur</li>
              </ul>
            </div>
            
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Features:</h3>
              <ul className="text-sm space-y-1 ml-4">
                <li>• Message queueing with retry logic</li>
                <li>• Automatic reconnection</li>
                <li>• State recovery across sessions</li>
                <li>• Multi-user isolation</li>
                <li>• Race condition prevention</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};