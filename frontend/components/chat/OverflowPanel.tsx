"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Terminal, 
  Clock, 
  Database, 
  Activity,
  AlertCircle,
  Download,
  Search,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { cn } from '@/lib/utils';

interface OverflowPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = 'events' | 'timeline' | 'state' | 'metrics' | 'errors';

export const OverflowPanel: React.FC<OverflowPanelProps> = ({ isOpen, onClose }) => {
  const { 
    currentRunId, 
    messages, 
    wsEventBuffer,
    executedAgents,
    performanceMetrics,
    activeThreadId
  } = useUnifiedChatStore();
  const [activeTab, setActiveTab] = useState<TabType>('events');
  const [eventFilter, setEventFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isMaximized, setIsMaximized] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Get events from WebSocket buffer
  const events = wsEventBuffer?.getAll?.() || [];
  
  // Filter events based on search and filter
  const filteredEvents = events.filter((event: any) => {
    if (eventFilter && event.type !== eventFilter) return false;
    if (searchQuery) {
      const eventString = JSON.stringify(event).toLowerCase();
      return eventString.includes(searchQuery.toLowerCase());
    }
    return true;
  });

  // Get unique event types for filter dropdown
  const eventTypes = [...new Set(events.map((e: any) => e.type))];

  // Export debug data
  const exportDebugData = () => {
    const debugData = {
      timestamp: new Date().toISOString(),
      currentRunId,
      activeThreadId,
      events: wsEventBuffer.exportAsJSON(),
      executedAgents: Array.from(executedAgents.entries()),
      performanceMetrics,
      messages: messages.slice(-20), // Last 20 messages
      userAgent: navigator.userAgent,
      bufferStats: wsEventBuffer.getStats()
    };

    const blob = new Blob([JSON.stringify(debugData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `netra-debug-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Keyboard shortcut to toggle panel
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        if (isOpen) {
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const tabs = [
    { id: 'events' as TabType, label: 'Events', icon: Terminal },
    { id: 'timeline' as TabType, label: 'Timeline', icon: Clock },
    { id: 'state' as TabType, label: 'State', icon: Database },
    { id: 'metrics' as TabType, label: 'Metrics', icon: Activity },
    { id: 'errors' as TabType, label: 'Errors', icon: AlertCircle },
  ];

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
            isMaximized ? "h-[80vh]" : "h-[400px]",
            "transition-[height] duration-300"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-gray-50/50">
            <div className="flex items-center space-x-4">
              <h3 className="text-sm font-semibold text-gray-900">Debug Panel</h3>
              <div className="flex space-x-1">
                {tabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200",
                      activeTab === tab.id
                        ? "bg-emerald-100 text-emerald-700 shadow-sm"
                        : "text-gray-600 hover:bg-gray-100"
                    )}
                  >
                    <div className="flex items-center space-x-1.5">
                      <tab.icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="pl-8 pr-3 py-1.5 text-xs bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                />
              </div>
              
              {/* Event Filter */}
              {activeTab === 'events' && eventTypes.length > 0 && (
                <select
                  value={eventFilter}
                  onChange={(e) => setEventFilter(e.target.value)}
                  className="px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                >
                  <option value="">All Events</option>
                  {eventTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              )}
              
              {/* Export Button */}
              <button
                onClick={exportDebugData}
                className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
                title="Export Debug Data"
              >
                <Download className="w-4 h-4" />
              </button>
              
              {/* Maximize/Minimize */}
              <button
                onClick={() => setIsMaximized(!isMaximized)}
                className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
              >
                {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
              
              {/* Close */}
              <button
                onClick={onClose}
                className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'events' && (
              <div className="h-full overflow-y-auto p-4" ref={scrollAreaRef}>
                {filteredEvents.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400">
                    <Terminal className="w-12 h-12 mb-2 opacity-50" />
                    <p className="text-sm">No events captured</p>
                    <p className="text-xs mt-1">Events will appear here as they occur</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredEvents.map((event, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.01 }}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <span className="px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700 rounded">
                                {event.type}
                              </span>
                              <span className="text-xs text-gray-500">
                                {new Date(event.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <pre className="mt-2 text-xs text-gray-700 overflow-x-auto">
                              {JSON.stringify(event.payload, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'timeline' && (
              <div className="p-4">
                <div className="text-center text-gray-400 mt-8">
                  <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Timeline view coming soon</p>
                </div>
              </div>
            )}

            {activeTab === 'state' && (
              <div className="p-4">
                <div className="text-center text-gray-400 mt-8">
                  <Database className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">State inspector coming soon</p>
                </div>
              </div>
            )}

            {activeTab === 'metrics' && (
              <div className="p-4">
                <div className="text-center text-gray-400 mt-8">
                  <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Performance metrics coming soon</p>
                </div>
              </div>
            )}

            {activeTab === 'errors' && (
              <div className="p-4">
                <div className="text-center text-gray-400 mt-8">
                  <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No errors detected</p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};