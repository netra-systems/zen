"use client";

import React from 'react';
import { motion } from 'framer-motion';
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
import { cn } from '@/lib/utils';
import { WSEventData } from './event-management';

export type TabType = 'events' | 'timeline' | 'state' | 'metrics' | 'errors';

export interface TabConfig {
  id: TabType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export interface PanelHeaderProps {
  activeTab: TabType;
  tabs: TabConfig[];
  searchQuery: string;
  eventFilter: string;
  eventTypes: string[];
  isMaximized: boolean;
  onTabChange: (tab: TabType) => void;
  onSearchChange: (query: string) => void;
  onFilterChange: (filter: string) => void;
  onExport: () => void;
  onToggleMaximize: () => void;
  onClose: () => void;
}

export interface EventListProps {
  events: WSEventData[];
  scrollAreaRef: React.RefObject<HTMLDivElement>;
}

export interface EmptyTabProps {
  icon: React.ComponentType<{ className?: string }>;
  message: string;
}

const createSearchInput = (props: Pick<PanelHeaderProps, 'searchQuery' | 'onSearchChange'>) => (
  <div className="relative">
    <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
    <input
      type="text"
      value={props.searchQuery}
      onChange={(e) => props.onSearchChange(e.target.value)}
      placeholder="Search..."
      className="pl-8 pr-3 py-1.5 text-xs bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
    />
  </div>
);

const createEventFilter = (props: Pick<PanelHeaderProps, 'activeTab' | 'eventFilter' | 'eventTypes' | 'onFilterChange'>) => {
  if (props.activeTab !== 'events' || props.eventTypes.length === 0) return null;
  
  return (
    <select
      value={props.eventFilter}
      onChange={(e) => props.onFilterChange(e.target.value)}
      className="px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
    >
      <option value="">All Events</option>
      {props.eventTypes.map(type => (
        <option key={type} value={type}>{type}</option>
      ))}
    </select>
  );
};

const createActionButton = (
  icon: React.ComponentType<{ className?: string }>,
  onClick: () => void,
  title?: string
) => (
  <button
    onClick={onClick}
    className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
    title={title}
  >
    {React.createElement(icon, { className: "w-4 h-4" })}
  </button>
);

const createTabButton = (
  tab: TabConfig,
  isActive: boolean,
  onClick: () => void
) => (
  <button
    key={tab.id}
    onClick={onClick}
    className={cn(
      "px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200",
      isActive
        ? "bg-emerald-100 text-emerald-700 shadow-sm"
        : "text-gray-600 hover:bg-gray-100"
    )}
  >
    <div className="flex items-center space-x-1.5">
      <tab.icon className="w-3.5 h-3.5" />
      <span>{tab.label}</span>
    </div>
  </button>
);

export const PanelHeader: React.FC<PanelHeaderProps> = (props) => {
  const searchInput = createSearchInput(props);
  const eventFilter = createEventFilter(props);
  const exportButton = createActionButton(Download, props.onExport, "Export Debug Data");
  const maximizeButton = createActionButton(
    props.isMaximized ? Minimize2 : Maximize2,
    props.onToggleMaximize
  );
  const closeButton = createActionButton(X, props.onClose);

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-gray-50/50">
      <div className="flex items-center space-x-4">
        <h3 className="text-sm font-semibold text-gray-900">Debug Panel</h3>
        <div className="flex space-x-1">
          {props.tabs.map(tab => createTabButton(tab, props.activeTab === tab.id, () => props.onTabChange(tab.id)))}
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        {searchInput}
        {eventFilter}
        {exportButton}
        {maximizeButton}
        {closeButton}
      </div>
    </div>
  );
};

const createEventItem = (event: WSEventData, index: number) => (
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
            {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'N/A'}
          </span>
        </div>
        <pre className="mt-2 text-xs text-gray-700 overflow-x-auto">
          {JSON.stringify(event.payload, null, 2)}
        </pre>
      </div>
    </div>
  </motion.div>
);

const createEmptyState = (events: WSEventData[]) => {
  if (events.length > 0) return null;
  
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-400">
      <Terminal className="w-12 h-12 mb-2 opacity-50" />
      <p className="text-sm">No events captured</p>
      <p className="text-xs mt-1">Events will appear here as they occur</p>
    </div>
  );
};

export const EventList: React.FC<EventListProps> = ({ events, scrollAreaRef }) => {
  const emptyState = createEmptyState(events);
  
  return (
    <div className="h-full overflow-y-auto p-4" ref={scrollAreaRef}>
      {emptyState || (
        <div className="space-y-2">
          {events.map((event, index) => createEventItem(event, index))}
        </div>
      )}
    </div>
  );
};

export const EmptyTab: React.FC<EmptyTabProps> = ({ icon: Icon, message }) => (
  <div className="p-4">
    <div className="text-center text-gray-400 mt-8">
      <Icon className="w-12 h-12 mx-auto mb-2 opacity-50" />
      <p className="text-sm">{message}</p>
    </div>
  </div>
);

export const TABS: TabConfig[] = [
  { id: 'events', label: 'Events', icon: Terminal },
  { id: 'timeline', label: 'Timeline', icon: Clock },
  { id: 'state', label: 'State', icon: Database },
  { id: 'metrics', label: 'Metrics', icon: Activity },
  { id: 'errors', label: 'Errors', icon: AlertCircle },
];