import React from 'react';

export const Thinking = () => {
  return (
    <div className="flex items-center space-x-2">
      <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse"></div>
      <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse delay-75"></div>
      <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse delay-150"></div>
    </div>
  );
};