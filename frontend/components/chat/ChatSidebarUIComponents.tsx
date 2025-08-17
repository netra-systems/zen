/**
 * Basic UI components for ChatSidebar
 * All functions are ≤8 lines for architecture compliance
 */

"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Plus, Search, Shield, Database, 
  Sparkles, Users, Filter 
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  NewChatButtonProps, AdminControlsProps, SearchBarProps,
  FilterOption, FilterType
} from './ChatSidebarTypes';

const getSpinningPlusIcon = () => (
  <motion.div
    animate={{ rotate: 360 }}
    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
  >
    <Plus className="w-5 h-5" />
  </motion.div>
);

export const NewChatButton: React.FC<NewChatButtonProps> = ({ 
  isCreatingThread, isProcessing, onNewChat 
}) => (
  <button
    onClick={onNewChat}
    disabled={isCreatingThread || isProcessing}
    data-testid="new-chat-button"
    className={cn(
      "w-full flex items-center justify-center space-x-2 px-4 py-3",
      "bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg",
      "transition-all duration-200 transform hover:scale-[1.02]",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      "shadow-sm hover:shadow-md"
    )}
  >
    {isCreatingThread ? getSpinningPlusIcon() : <Plus className="w-5 h-5" />}
    <span className="font-medium">New Chat</span>
  </button>
);

export const SearchBar: React.FC<SearchBarProps> = ({
  searchQuery, showAllThreads, onSearchChange
}) => (
  <div className="p-4 border-b border-gray-100">
    <div className="relative">
      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder={showAllThreads ? "Search all system chats..." : "Search conversations..."}
        data-testid="search-input"
        className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all duration-200"
      />
    </div>
  </div>
);

const getFilterOptions = (): FilterOption[] => [
  { key: 'all', icon: Filter, label: 'All' },
  { key: 'corpus', icon: Database, label: 'Corpus' },
  { key: 'synthetic', icon: Sparkles, label: 'Synthetic' },
  { key: 'users', icon: Users, label: 'Users' },
];

const FilterButton: React.FC<{
  option: FilterOption;
  isActive: boolean;
  onClick: () => void;
}> = ({ option, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={cn(
      "flex items-center space-x-1 px-2 py-1 text-xs rounded-md transition-colors",
      isActive
        ? "bg-purple-100 text-purple-700 border border-purple-300"
        : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
    )}
  >
    <option.icon className="w-3 h-3" />
    <span>{option.label}</span>
  </button>
);

export const AdminControls: React.FC<AdminControlsProps> = ({
  isAdmin, showAllThreads, filterType, onToggleAllThreads, onFilterChange
}) => {
  if (!isAdmin) return null;
  
  return (
    <div className="px-4 pt-2 pb-0">
      <div className="flex items-center justify-between p-2 bg-purple-50 rounded-lg border border-purple-200">
        <div className="flex items-center space-x-2">
          <Shield className="w-4 h-4 text-purple-600" />
          <span className="text-sm font-medium text-purple-900">Admin View</span>
        </div>
        <button
          onClick={onToggleAllThreads}
          className={cn(
            "px-3 py-1 text-xs font-medium rounded-md transition-colors",
            showAllThreads 
              ? "bg-purple-600 text-white" 
              : "bg-white text-purple-600 border border-purple-300"
          )}
        >
          {showAllThreads ? 'All System Chats' : 'My Chats'}
        </button>
      </div>
      
      {showAllThreads && (
        <div className="flex flex-wrap gap-1 mt-2">
          {getFilterOptions().map((option) => (
            <FilterButton
              key={option.key}
              option={option}
              isActive={filterType === option.key}
              onClick={() => onFilterChange(option.key)}
            />
          ))}
        </div>
      )}
    </div>
  );
};