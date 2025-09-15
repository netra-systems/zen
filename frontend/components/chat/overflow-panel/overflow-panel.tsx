"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Database, Activity, AlertCircle } from 'lucide-react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { cn } from '@/lib/utils';
import { useEventManagement } from './event-management';
import { exportDebugData, DebugExportOptions } from './debug-export';
import { useResponsiveHeight } from '@/hooks/useWindowSize';
import { 
  PanelHeader, 
  EventList, 
  EmptyTab, 
  TABS,
  TabType 
} from './overflow-panel-ui';

interface OverflowPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const OverflowPanel: React.FC<OverflowPanelProps> = ({ isOpen, onClose }) => {
  const { 
    currentRunId, 
    messages, 
    wsEventBuffer,
    wsEventBufferVersion,
    executedAgents,
    performanceMetrics,
    activeThreadId
  } = useUnifiedChatStore();

  const [activeTab, setActiveTab] = useState<TabType>('events');
  const [isMaximized, setIsMaximized] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const eventManagement = useEventManagement(wsEventBuffer, wsEventBufferVersion);
  const { secondary, compact } = useResponsiveHeight();

  const scrollEventsToBottom = () => {
    if (scrollAreaRef.current && activeTab === 'events') {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  };

  const handleExportDebugData = () => {
    const options: DebugExportOptions = {
      currentRunId,
      activeThreadId,
      wsEventBuffer,
      executedAgents,
      performanceMetrics,
      messages,
    };
    exportDebugData(options);
  };

  const handleKeyboardShortcut = (e: KeyboardEvent) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
      if (isOpen) {
        onClose();
      }
    }
  };

  // Auto-scroll to bottom when new events arrive (if events tab is active)
  useEffect(() => {
    scrollEventsToBottom();
  }, [eventManagement.events.length, activeTab]);

  // Keyboard shortcut to toggle panel
  useEffect(() => {
    window.addEventListener('keydown', handleKeyboardShortcut);
    return () => window.removeEventListener('keydown', handleKeyboardShortcut);
  }, [isOpen, onClose]);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'events':
        return (
          <EventList 
            events={eventManagement.filteredEvents} 
            scrollAreaRef={scrollAreaRef} 
          />
        );
      case 'timeline':
        return <EmptyTab icon={Clock} message="Timeline view coming soon" />;
      case 'state':
        return <EmptyTab icon={Database} message="State inspector coming soon" />;
      case 'metrics':
        return <EmptyTab icon={Activity} message="Performance metrics coming soon" />;
      case 'errors':
        return <EmptyTab icon={AlertCircle} message="No errors detected" />;
      default:
        return null;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 100 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 100 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={cn(
            "fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-xl border-t border-gray-200 shadow-2xl z-50",
            "transition-[height] duration-300 overflow-hidden"
          )}
          style={{
            height: isMaximized ? `${secondary}px` : `${compact}px`,
            maxHeight: isMaximized ? '80vh' : '60vh'
          }}
          data-testid="overflow-panel"
        >
          <PanelHeader
            activeTab={activeTab}
            tabs={TABS}
            searchQuery={eventManagement.searchQuery}
            eventFilter={eventManagement.eventFilter}
            eventTypes={eventManagement.eventTypes}
            isMaximized={isMaximized}
            onTabChange={setActiveTab}
            onSearchChange={eventManagement.setSearchQuery}
            onFilterChange={eventManagement.setEventFilter}
            onExport={handleExportDebugData}
            onToggleMaximize={() => setIsMaximized(!isMaximized)}
            onClose={onClose}
          />

          <div className="flex-1 overflow-hidden">
            {renderTabContent()}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};