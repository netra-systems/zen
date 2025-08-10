"use client";

import React, { useState, useEffect, useRef } from 'react';
import { UltraChatHeader } from '@/components/chat/UltraChatHeader';
import { UltraMessageItem } from '@/components/chat/UltraMessageItem';
import { AgentStatusCard } from '@/components/chat/AgentStatusCard';
import { MessageInput } from '@/components/chat/MessageInput';
import { StopButton } from '@/components/chat/StopButton';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { ThreadSidebar } from '@/components/chat/ThreadSidebar';
import { FinalReportView } from '@/components/chat/FinalReportView';
import { useChatStore } from '@/store/chat';
import { useChatWebSocket } from '@/hooks/useChatWebSocket';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { ArrowDown, Sparkles } from 'lucide-react';

const UltraMainChat: React.FC = () => {
  const { 
    isProcessing, 
    messages, 
    currentSubAgent,
    subAgentStatus 
  } = useChatStore();
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showAgentStatus, setShowAgentStatus] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [showFinalReport, setShowFinalReport] = useState(false);
  
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isUserScrolling = useRef(false);
  
  // Connect WebSocket messages to chat store
  useChatWebSocket();

  const hasMessages = messages.filter(m => m.displayed_to_user).length > 0;
  const displayedMessages = messages.filter(m => m.displayed_to_user);

  // Auto-scroll logic
  const scrollToBottom = (smooth = true) => {
    if (messagesEndRef.current && !isUserScrolling.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: smooth ? 'smooth' : 'auto',
        block: 'end'
      });
    }
  };

  // Handle scroll events to detect user scrolling
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      
      // Show scroll button when not at bottom
      setShowScrollButton(!isAtBottom);
      
      // Detect user scrolling
      if (!isAtBottom) {
        isUserScrolling.current = true;
      } else {
        isUserScrolling.current = false;
      }
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Mock agent status data (replace with real data from WebSocket)
  const agentStatusData = {
    agentName: currentSubAgent || 'Netra AI',
    status: isProcessing ? 'executing' : 'idle' as const,
    currentAction: isProcessing ? 'Processing your request...' : undefined,
    progress: isProcessing ? 65 : 0,
    tools: isProcessing ? [
      { name: 'cost_analysis', status: 'completed' as const, duration: 2500 },
      { name: 'latency_bottleneck', status: 'running' as const },
      { name: 'kv_cache_optimization', status: 'pending' as const }
    ] : [],
    metrics: {
      cpu: 45,
      memory: 62,
      apiCalls: 12,
      tokensUsed: 3456
    }
  };

  // Check if we should show final report
  useEffect(() => {
    const hasReport = messages.some(m => 
      m.type === 'report' || 
      (m.sub_agent_name === 'ReportingSubAgent' && m.content?.includes('## Final Report'))
    );
    if (hasReport && !isProcessing) {
      setShowFinalReport(true);
    }
  }, [messages, isProcessing]);

  return (
    <div className={cn(
      "flex h-screen",
      "bg-gradient-to-br from-gray-50 via-white to-gray-50",
      isDarkMode && "from-gray-900 via-gray-800 to-gray-900"
    )}>
      {/* Thread Sidebar */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-[280px] border-r bg-white/50 backdrop-blur-sm"
          >
            <ThreadSidebar />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 max-w-full overflow-hidden">
        {/* Header */}
        <UltraChatHeader
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onNewChat={() => {/* Implement new chat */}}
          onOpenSettings={() => {/* Implement settings */}}
          onOpenHelp={() => {/* Implement help */}}
          isSidebarOpen={isSidebarOpen}
          isDarkMode={isDarkMode}
          onToggleDarkMode={() => setIsDarkMode(!isDarkMode)}
        />
        
        {/* Content Area */}
        <div className="flex-grow flex overflow-hidden">
          {/* Messages Area */}
          <div className="flex-1 flex flex-col">
            {/* Agent Status Card */}
            {isProcessing && showAgentStatus && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="px-6 pt-4"
              >
                <AgentStatusCard
                  {...agentStatusData}
                  onCancel={() => {/* Implement cancel */}}
                  onPause={() => {/* Implement pause */}}
                  onResume={() => {/* Implement resume */}}
                />
              </motion.div>
            )}

            {/* Messages Container */}
            <div 
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto px-2 py-4 scroll-smooth"
            >
              <AnimatePresence initial={false}>
                {/* Empty State */}
                {!hasMessages && (
                  <motion.div
                    key="empty-state"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3 }}
                    className="flex flex-col items-center justify-center h-full min-h-[400px]"
                  >
                    <motion.div
                      initial={{ y: -20 }}
                      animate={{ y: 0 }}
                      transition={{ delay: 0.1 }}
                      className="text-center space-y-4"
                    >
                      <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 inline-block">
                        <Sparkles className="w-12 h-12 text-white" />
                      </div>
                      <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        Welcome to Netra AI
                      </h2>
                      <p className="text-gray-500 max-w-md mx-auto">
                        The world's most intelligent AI optimization platform. Start by typing a message or selecting an example below.
                      </p>
                    </motion.div>
                    
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className="mt-8 w-full max-w-3xl"
                    >
                      <ExamplePrompts />
                    </motion.div>
                  </motion.div>
                )}

                {/* Messages List */}
                {displayedMessages.map((msg, index) => (
                  <UltraMessageItem
                    key={msg.id || `msg-${index}`}
                    message={msg}
                    isCurrentAgent={
                      isProcessing && 
                      index === displayedMessages.length - 1 &&
                      msg.sub_agent_name === currentSubAgent
                    }
                  />
                ))}
              </AnimatePresence>
              
              {/* Scroll anchor */}
              <div ref={messagesEndRef} className="h-4" />
            </div>

            {/* Scroll to Bottom Button */}
            <AnimatePresence>
              {showScrollButton && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 20 }}
                  className="absolute bottom-32 right-8"
                >
                  <Button
                    onClick={() => {
                      isUserScrolling.current = false;
                      scrollToBottom();
                    }}
                    size="icon"
                    className="rounded-full shadow-lg bg-white hover:bg-gray-100"
                  >
                    <ArrowDown className="w-4 h-4" />
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Panel - Final Report */}
          <AnimatePresence>
            {showFinalReport && (
              <motion.div
                initial={{ x: 320 }}
                animate={{ x: 0 }}
                exit={{ x: 320 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="w-[320px] border-l bg-white/50 backdrop-blur-sm overflow-y-auto"
              >
                <div className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">Analysis Report</h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowFinalReport(false)}
                    >
                      Close
                    </Button>
                  </div>
                  <FinalReportView
                    data_result={{}}
                    optimizations_result={{}}
                    action_plan_result={{}}
                    execution_metrics={{
                      total_duration: 15000,
                      agent_timings: [],
                      tool_calls: []
                    }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {/* Input Area */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className={cn(
            "border-t",
            "bg-white/95 backdrop-blur-sm shadow-lg",
            isDarkMode && "bg-gray-900/95 border-gray-800"
          )}
        >
          <div className="px-6 py-4 max-w-5xl mx-auto w-full">
            <div className="space-y-3">
              <MessageInput />
              
              {isProcessing && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="flex justify-center"
                >
                  <StopButton />
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default UltraMainChat;