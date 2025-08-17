/**
 * Footer and pagination components for ChatSidebar
 * All functions are ≤8 lines for architecture compliance
 */

"use client";

import React from 'react';
import { ChevronLeft, ChevronRight, Database, Sparkles } from 'lucide-react';
import { PaginationProps, FooterProps } from './ChatSidebarTypes';

export const PaginationControls: React.FC<PaginationProps> = ({
  currentPage, totalPages, onPageChange
}) => {
  if (totalPages <= 1) return null;
  
  return (
    <div className="p-3 border-t border-gray-200 bg-white flex items-center justify-between">
      <button
        onClick={() => onPageChange(Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
        className="p-1.5 rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      
      <span className="text-xs text-gray-600">
        Page {currentPage} of {totalPages}
      </span>
      
      <button
        onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages}
        className="p-1.5 rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
};

export const Footer: React.FC<FooterProps> = ({
  threads, paginatedThreads, threadsPerPage, isAdmin
}) => (
  <div className="p-4 border-t border-gray-200 bg-gray-50">
    <p className="text-xs text-gray-500 text-center mb-2">
      {threads.length} conversation{threads.length !== 1 ? 's' : ''}
      {threads.length > threadsPerPage && ` (showing ${paginatedThreads.length})`}
    </p>
    
    {isAdmin && (
      <div className="flex flex-col space-y-1 mt-2">
        <button className="flex items-center justify-center space-x-2 p-2 text-xs bg-purple-100 text-purple-700 rounded-md hover:bg-purple-200 transition-colors">
          <Database className="w-3 h-3" />
          <span>Quick Create Corpus</span>
        </button>
        <button className="flex items-center justify-center space-x-2 p-2 text-xs bg-purple-100 text-purple-700 rounded-md hover:bg-purple-200 transition-colors">
          <Sparkles className="w-3 h-3" />
          <span>Generate Test Data</span>
        </button>
      </div>
    )}
  </div>
);