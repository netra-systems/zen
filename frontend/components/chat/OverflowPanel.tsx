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
  Filter,
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
  const { wsEventBuffer, performanceMetrics, activeThreadId, currentRunId } = useUnifiedChatStore();
  const [activeTab, setActiveTab] = useState<TabType>('events');
  const [eventFilter, setEventFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isMaximized, setIsMaximized] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Get events from circular buffer
  const events = wsEventBuffer?.getAll() || [];
  
  // Filter events based on search and filter
  const filteredEvents = events.filter(event => {
    if (eventFilter && event.type !== eventFilter) return false;
    if (searchQuery) {
      const eventString = JSON.stringify(event).toLowerCase();
      return eventString.includes(searchQuery.toLowerCase());
    }
    return true;
  });

  // Get unique event types for filter dropdown
  const eventTypes = [...new Set(events.map(e => e.type))];

  // Export debug data
  const exportDebugData = () => {
    const debugData = {
      timestamp: new Date().toISOString(),
      activeThreadId,
      currentRunId,
      events: events.slice(-100), // Last 100 events
      performanceMetrics,
      userAgent: navigator.userAgent,
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
        e.preventDefault();
        if (isOpen) onClose();
        else setIsMaximized(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const tabs = [
    { id: 'events' as TabType, label: 'WebSocket Events', icon: Terminal },
    { id: 'timeline' as TabType, label: 'Run Timeline', icon: Clock },
    { id: 'state' as TabType, label: 'Backend State', icon: Database },
    { id: 'metrics' as TabType, label: 'Performance', icon: Activity },
    { id: 'errors' as TabType, label: 'Errors', icon: AlertCircle },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className={cn(
            "fixed bottom-0 left-0 right-0 bg-gray-900 text-gray-100 shadow-2xl z-50",
            "border-t border-gray-700",
            isMaximized ? "h-full" : "h-96"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
            <div className="flex items-center space-x-4">
              <Terminal className="w-5 h-5 text-emerald-400" />
              <h3 className="font-mono text-sm font-semibold">Developer Console</h3>
              
              {/* Tabs */}
              <div className="flex space-x-1">
                {tabs.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "px-3 py-1 text-xs font-mono rounded transition-colors duration-200",
                      activeTab === tab.id 
                        ? "bg-gray-700 text-emerald-400" 
                        : "hover:bg-gray-700/50 text-gray-400"
                    )}
                  >
                    <tab.icon className="w-3 h-3 inline-block mr-1" />
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2">
              <button
                onClick={exportDebugData}
                className="p-1.5 hover:bg-gray-700 rounded transition-colors duration-200"
                title="Export Debug Data"
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsMaximized(!isMaximized)}
                className="p-1.5 hover:bg-gray-700 rounded transition-colors duration-200"
                title={isMaximized ? "Minimize" : "Maximize"}
              >
                {isMaximized ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-gray-700 rounded transition-colors duration-200"
                title="Close (Ctrl+Shift+D)"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {/* Tab Content */}
            {activeTab === 'events' && (
              <>
                {/* Filters */}
                <div className="px-4 py-2 bg-gray-800/50 border-b border-gray-700 flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <Filter className="w-4 h-4 text-gray-400" />
                    <select
                      value={eventFilter}
                      onChange={(e) => setEventFilter(e.target.value)}
                      className="bg-gray-700 text-gray-100 text-xs px-2 py-1 rounded border border-gray-600 focus:border-emerald-500 focus:outline-none"
                    >
                      <option value="">All Events</option>
                      {eventTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="flex items-center space-x-2 flex-1">
                    <Search className="w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search events..."
                      className="flex-1 bg-gray-700 text-gray-100 text-xs px-2 py-1 rounded border border-gray-600 focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  
                  <div className="text-xs text-gray-400">
                    {filteredEvents.length} / {events.length} events
                  </div>
                </div>

                {/* Event List */}
                <div className="flex-1 overflow-y-auto font-mono text-xs" ref={scrollAreaRef}>
                  {filteredEvents.map((event, index) => (
                    <div
                      key={`${event.timestamp}-${index}`}
                      className="px-4 py-2 border-b border-gray-800 hover:bg-gray-800/50 group"
                    >
                      <div className="flex items-start space-x-2">
                        <span className="text-gray-500 min-w-[140px]">
                          {new Date(event.timestamp).toLocaleTimeString('en-US', { 
                            hour12: false, 
                            hour: '2-digit', 
                            minute: '2-digit', 
                            second: '2-digit',
                            fractionalSecondDigits: 3 
                          })}
                        </span>
                        <span className={cn(
                          "px-2 py-0.5 rounded text-xs font-semibold min-w-[100px] text-center",
                          event.type.includes('error') ? "bg-red-900/50 text-red-400" :
                          event.type.includes('agent') ? "bg-purple-900/50 text-purple-400" :
                          event.type.includes('tool') ? "bg-blue-900/50 text-blue-400" :
                          "bg-gray-700 text-gray-300"
                        )}>
                          {event.type}
                        </span>
                        <div className="flex-1">
                          <pre className="text-gray-300 whitespace-pre-wrap break-all">
                            {JSON.stringify(event.payload, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {activeTab === 'timeline' && (
              <div className="flex-1 p-4">
                <div className="text-center text-gray-400 mt-8">
                  <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Run Timeline Visualization</p>
                  <p className="text-xs mt-2">Gantt chart of agent executions coming soon</p>
                </div>
              </div>
            )}

            {activeTab === 'state' && (
              <div className="flex-1 p-4 overflow-y-auto">
                <div className="space-y-4 font-mono text-xs">
                  <div>
                    <h4 className="text-emerald-400 mb-2">Active Thread</h4>
                    <div className="bg-gray-800 p-2 rounded">
                      <code>{activeThreadId || 'None'}</code>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-emerald-400 mb-2">Current Run</h4>
                    <div className="bg-gray-800 p-2 rounded">
                      <code>{currentRunId || 'None'}</code>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'metrics' && (
              <div className="flex-1 p-4 overflow-y-auto">
                <div className="grid grid-cols-2 gap-4">
                  {performanceMetrics && Object.entries(performanceMetrics).map(([key, value]) => (
                    <div key={key} className="bg-gray-800 p-3 rounded">
                      <div className="text-xs text-gray-400 mb-1">{key}</div>
                      <div className="text-lg font-mono text-emerald-400">{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'errors' && (
              <div className="flex-1 p-4">
                <div className="text-center text-gray-400 mt-8">
                  <AlertCircle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No errors detected</p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};