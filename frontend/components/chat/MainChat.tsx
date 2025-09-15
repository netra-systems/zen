"use client";

import React, { useState, useEffect, useRef } from 'react';
import { ChatHeader } from '@/components/chat/ChatHeader';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput, MessageInputRef } from '@/components/chat/MessageInput';
import { PersistentResponseCard } from '@/components/chat/PersistentResponseCard';
import { ExamplePrompts } from '@/components/chat/ExamplePrompts';
import { OverflowPanel } from '@/components/chat/OverflowPanel';
import { EventDiagnosticsPanel } from '@/components/chat/EventDiagnosticsPanel';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLoadingState } from '@/hooks/useLoadingState';
import { useEventProcessor } from '@/hooks/useEventProcessor';
import { useThreadNavigation } from '@/hooks/useThreadNavigation';
import { useInitializationCoordinator } from '@/hooks/useInitializationCoordinator';
import { useResponsiveHeight } from '@/hooks/useWindowSize';
import { logger } from '@/lib/logger';

// Helper Functions (8 lines max each)
const executeTestRun = async (
  setIsRunningTests: (running: boolean) => void,
  setTestResults: (results: any) => void
): Promise<void> => {
  setIsRunningTests(true);
  try {
    // Test functionality disabled - test file not available
    setTestResults({ error: 'Test functionality not available' });
  } catch (error) {
    handleTestExecutionError(error, setTestResults);
  } finally {
    setIsRunningTests(false);
  }
};

const handleTestExecutionError = (
  error: unknown,
  setTestResults: (results: any) => void
): void => {
  logger.error('Test execution failed:', error);
  setTestResults({ error: (error as Error).message });
};

const handleOverflowToggle = (
  e: KeyboardEvent,
  setIsOverflowOpen: (open: boolean | ((prev: boolean) => boolean)) => void
): void => {
  if (e.ctrlKey && e.shiftKey && e.key === 'D') {
    e.preventDefault();
    setIsOverflowOpen(prev => !prev);
  }
};

const handleDiagnosticsToggle = (
  e: KeyboardEvent,
  setShowEventDiagnostics: (show: boolean | ((prev: boolean) => boolean)) => void
): void => {
  if (e.ctrlKey && e.shiftKey && e.key === 'E') {
    e.preventDefault();
    setShowEventDiagnostics(prev => !prev);
  }
};

const handleMessageInputFocus = (
  e: KeyboardEvent,
  messageInputRef: React.RefObject<MessageInputRef>
): void => {
  if (e.ctrlKey && e.key === 'i') {
    e.preventDefault();
    messageInputRef.current?.focus();
  }
};

const createKeyboardHandler = (
  setIsOverflowOpen: (open: boolean | ((prev: boolean) => boolean)) => void,
  setShowEventDiagnostics: (show: boolean | ((prev: boolean) => boolean)) => void,
  messageInputRef: React.RefObject<MessageInputRef>
) => {
  return (e: KeyboardEvent) => {
    handleOverflowToggle(e, setIsOverflowOpen);
    handleDiagnosticsToggle(e, setShowEventDiagnostics);
    handleMessageInputFocus(e, messageInputRef);
  };
};
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { InitializationProgress } from '@/components/InitializationProgress';

const MainChat: React.FC = () => {
  const { 
    isProcessing, 
    messages,
    fastLayerData,
    mediumLayerData,
    slowLayerData,
    currentRunId,
    activeThreadId,
    isThreadLoading,
    handleWebSocketEvent
  } = useUnifiedChatStore();
  
  // Thread navigation with URL sync
  const { currentThreadId, isNavigating } = useThreadNavigation();
  
  // Coordinate initialization to prevent re-renders
  const { state: initState, isInitialized } = useInitializationCoordinator();
  
  const { messages: wsMessages } = useWebSocket();
  const [isCardCollapsed, setIsCardCollapsed] = useState(false);
  const [isOverflowOpen, setIsOverflowOpen] = useState(false);
  const [showEventDiagnostics, setShowEventDiagnostics] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [isRunningTests, setIsRunningTests] = useState(false);
  
  // State for tracking first user interaction to hide welcome message
  const [hasUserStartedTyping, setHasUserStartedTyping] = useState(false);
  
  // Ref for MessageInput to enable focus from keyboard shortcuts
  const messageInputRef = useRef<MessageInputRef>(null);
  
  // Ref for main scrollable content area and scroll position preservation
  const mainContentRef = useRef<HTMLDivElement>(null);
  const [scrollPosition, setScrollPosition] = useState(0);
  const [shouldPreserveScroll, setShouldPreserveScroll] = useState(false);
  
  // Use responsive height hook for better height management
  const { primary: responsiveHeight } = useResponsiveHeight();
  
  // Use new loading state hook for clean state management
  const {
    shouldShowLoading,
    shouldShowEmptyState,
    shouldShowExamplePrompts,
    loadingMessage
  } = useLoadingState();
  
  // Process WebSocket messages with race condition prevention
  const eventProcessor = useEventProcessor(
    wsMessages,
    handleWebSocketEvent,
    {
      maxQueueSize: 500,
      duplicateWindowMs: 3000,
      processingTimeoutMs: 5000,
      enableDeduplication: true
    }
  );

  // Test runner function
  const runTests = async () => {
    await executeTestRun(setIsRunningTests, setTestResults);
  };

  const hasMessages = messages.length > 0;
  
  // Thread loading is now handled via WebSocket events in the store
  // The handleWebSocketEvent function in useUnifiedChatStore will process
  // 'thread_loaded' events and automatically update the messages
  const showResponseCard = currentRunId !== null || isProcessing;
  const isThreadSwitching = (isThreadLoading || isNavigating) && !isProcessing;

  // Auto-collapse card after completion
  useEffect(() => {
    if (slowLayerData?.finalReport && !isProcessing) {
      const timer = setTimeout(() => {
        setIsCardCollapsed(true);
      }, 2000); // 2 seconds after completion
      
      return () => clearTimeout(timer);
    }
  }, [slowLayerData?.finalReport, isProcessing]);

  // Reset collapse state when new processing starts
  useEffect(() => {
    if (isProcessing) {
      setIsCardCollapsed(false);
    }
  }, [isProcessing]);

  // Reset first interaction state when starting new thread (no active thread)
  useEffect(() => {
    if (!activeThreadId && !currentThreadId && messages.length === 0) {
      setHasUserStartedTyping(false);
    }
  }, [activeThreadId, currentThreadId, messages.length]);

  // Callback for first user interaction
  const handleFirstInteraction = () => {
    setHasUserStartedTyping(true);
  };

  // Scroll position preservation logic
  useEffect(() => {
    const mainContent = mainContentRef.current;
    if (!mainContent) return;

    const handleScroll = () => {
      if (!shouldPreserveScroll) {
        setScrollPosition(mainContent.scrollTop);
      }
    };

    mainContent.addEventListener('scroll', handleScroll, { passive: true });
    return () => mainContent.removeEventListener('scroll', handleScroll);
  }, [shouldPreserveScroll]);

  // Preserve scroll position when thread changes
  useEffect(() => {
    if (shouldPreserveScroll && mainContentRef.current) {
      mainContentRef.current.scrollTop = scrollPosition;
      setShouldPreserveScroll(false);
    }
  }, [shouldPreserveScroll, scrollPosition]);

  // Set scroll preservation flag when switching threads
  useEffect(() => {
    if (isNavigating || isThreadLoading) {
      setShouldPreserveScroll(true);
    }
  }, [isNavigating, isThreadLoading]);

  // Keyboard shortcuts for panels and diagnostics
  useEffect(() => {
    const handleKeyDown = createKeyboardHandler(setIsOverflowOpen, setShowEventDiagnostics, messageInputRef);
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Get initialization state for progress display
  const { phase, progress } = initState;
  const { status: wsStatus } = useWebSocket();
  
  // Show loading state while initializing
  // Fixed: Only show loading if init is not complete, not based on shouldShowLoading
  // which can get stuck after initialization completes
  if (!isInitialized || phase !== 'ready') {
    return (
      <InitializationProgress 
        phase={phase}
        progress={progress}
        connectionStatus={wsStatus}
        error={phase === 'error' ? loadingMessage : undefined}
      />
    );
  }

  return (
    <div 
      className="flex flex-col h-full bg-gradient-to-br from-gray-50 via-white to-gray-50 overflow-hidden" 
      data-testid="main-chat"
      style={{ maxHeight: `${responsiveHeight}px` }}
    >
      {/* Chat Header - Fixed at top */}
      <div className="flex-shrink-0">
        <ChatHeader />
      </div>
      
      {/* Scrollable Content Area - Only scrollable element with independent scrolling */}
      <div 
        ref={mainContentRef}
        className="flex-1 overflow-y-auto overflow-x-hidden scroll-smooth" 
        data-testid="main-content"
        style={{ 
          scrollBehavior: 'smooth',
          WebkitOverflowScrolling: 'touch', // iOS smooth scrolling
        }}
      >
            {/* Empty State with Example Prompts - shown when no thread is selected OR thread selected but no messages */}
            <AnimatePresence mode="wait">
              {(shouldShowEmptyState || shouldShowExamplePrompts) && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="flex flex-col h-full"
                >
                  {/* Welcome Header - only show for empty state (no thread) and user hasn't started typing */}
                  <AnimatePresence>
                    {shouldShowEmptyState && !hasUserStartedTyping && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ delay: 0.1, duration: 0.3 }}
                        className="text-center mb-2 px-4"
                      >
                      <div className="w-16 h-16 mx-auto bg-gradient-to-br from-emerald-100 to-purple-100 rounded-full flex items-center justify-center mb-2">
                        <svg className="w-10 h-10 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <h1 className="text-2xl font-bold text-gray-900 mb-1">Welcome to Netra AI</h1>
                      <p className="text-lg text-gray-600 mb-2">
                        Your AI-powered optimization platform for reducing costs and improving performance
                      </p>
                      <div className="bg-blue-50 rounded-lg p-3 mb-2 max-w-2xl mx-auto">
                        <h3 className="text-base font-semibold text-blue-900 mb-1">Get Started in 3 Easy Steps:</h3>
                        <div className="space-y-2 text-left">
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">1</span>
                            <span>Choose an example prompt below or type your own optimization request</span>
                          </div>
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">2</span>
                            <span>Describe your current setup, performance requirements, and budget constraints</span>
                          </div>
                          <div className="flex items-center text-blue-800">
                            <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3">3</span>
                            <span>Get AI-powered recommendations to optimize your infrastructure</span>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                    )}
                  </AnimatePresence>
                  
                  {/* Example Prompts Section */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: shouldShowEmptyState && !hasUserStartedTyping ? 0.2 : 0 }}
                    className="mt-2"
                  >
                    <ExamplePrompts forceCollapsed={hasUserStartedTyping} />
                  </motion.div>
                  
                  {/* Quick tip - only show if user hasn't started typing */}
                  <AnimatePresence>
                    {!hasUserStartedTyping && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ delay: shouldShowEmptyState ? 0.4 : 0.2, duration: 0.3 }}
                        className="text-center mt-2 px-4"
                      >
                        <p className="text-gray-500 text-sm">
                          💡 Try typing something like: &quot;I need to reduce my AI costs by 30% while maintaining quality&quot;
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}
            </AnimatePresence>
            
            {/* Thread Loading Indicator */}
            {isThreadSwitching && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center justify-center h-32"
              >
                <div className="flex flex-col items-center gap-2 p-3 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  <div className="text-sm text-gray-600">Loading conversation...</div>
                  {(activeThreadId || currentThreadId) && (
                    <div className="text-xs text-gray-400">
                      Thread: {(activeThreadId || currentThreadId)!.slice(0, 8)}...
                    </div>
                  )}
                </div>
              </motion.div>
            )}
            
            {/* Message History */}
            {!shouldShowEmptyState && !isThreadSwitching && <MessageList />}
            
            {/* Processing Indicator - Required for tests */}
            {isProcessing && !isThreadSwitching && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="px-4 py-2"
                data-testid="agent-processing"
              >
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span>Processing your request...</span>
                </div>
              </motion.div>
            )}
            
            {/* Persistent Response Card - Shows current processing */}
            <AnimatePresence>
              {showResponseCard && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  className="px-4 py-3 max-w-3xl mx-auto"
                >
                  <PersistentResponseCard
                    fastLayerData={fastLayerData}
                    mediumLayerData={mediumLayerData}
                    slowLayerData={slowLayerData}
                    isProcessing={isProcessing}
                    isCollapsed={isCardCollapsed}
                    onToggleCollapse={() => setIsCardCollapsed(!isCardCollapsed)}
                  />
                </motion.div>
              )}
            </AnimatePresence>
      </div>
      
      {/* Chat Input - Fixed at bottom */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="flex-shrink-0 border-t bg-white/95 backdrop-blur-sm shadow-lg"
      >
        <div className="px-6 py-4 max-w-3xl mx-auto w-full">
          <MessageInput 
            ref={messageInputRef} 
            onFirstInteraction={handleFirstInteraction}
          />
        </div>
      </motion.div>
      
      {/* Overflow Debug Panel */}
      <OverflowPanel isOpen={isOverflowOpen} onClose={() => setIsOverflowOpen(false)} />
      
      {/* Event Processing Diagnostics Panel */}
      <EventDiagnosticsPanel
        showEventDiagnostics={showEventDiagnostics}
        setShowEventDiagnostics={setShowEventDiagnostics}
        eventProcessor={eventProcessor}
        wsMessages={wsMessages}
        testResults={testResults}
        setTestResults={setTestResults}
        isRunningTests={isRunningTests}
        setIsRunningTests={setIsRunningTests}
      />
    </div>
  );
};

export default MainChat;