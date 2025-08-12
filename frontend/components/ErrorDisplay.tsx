'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Copy, Check } from 'lucide-react';

interface ErrorDisplayProps {
  error: Error | string | null | undefined;
}

export const ErrorDisplay = ({ error }: ErrorDisplayProps) => {
  const [isCopied, setIsCopied] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  if (!error) return null;

  const errorMessage = typeof error === 'string'
    ? error
    : JSON.stringify(error, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(errorMessage);
    setIsCopied(true);
    
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // Set new timeout with proper cleanup
    timeoutRef.current = setTimeout(() => {
      setIsCopied(false);
      timeoutRef.current = null;
    }, 2000);
  };

  return (
    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md relative mb-6" role="alert">
      <div className="flex justify-between items-start">
        <pre className="text-sm whitespace-pre-wrap break-words font-sans">
          {errorMessage}
        </pre>
        <Button variant="ghost" size="icon" onClick={handleCopy} className="ml-4 flex-shrink-0 h-8 w-8">
          {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
};