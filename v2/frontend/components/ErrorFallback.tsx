'use client';

import React from 'react';

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({ 
  error, 
  resetErrorBoundary 
}) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
        <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        
        <h2 className="mt-4 text-xl font-semibold text-center text-gray-900">
          Something went wrong
        </h2>
        
        <p className="mt-2 text-sm text-center text-gray-600">
          An unexpected error has occurred. Please try again.
        </p>
        
        {process.env.NODE_ENV === 'development' && (
          <details className="mt-4 p-4 bg-gray-50 rounded text-xs">
            <summary className="cursor-pointer font-medium text-gray-700">
              Error details
            </summary>
            <pre className="mt-2 whitespace-pre-wrap text-red-600">
              {error.message}
            </pre>
            {error.stack && (
              <pre className="mt-2 whitespace-pre-wrap text-gray-600 text-xs">
                {error.stack}
              </pre>
            )}
          </details>
        )}
        
        <button
          onClick={resetErrorBoundary}
          className="mt-6 w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
};