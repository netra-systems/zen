import React from 'react';
import { Loader2 } from 'lucide-react';
import { Progress } from './ui/progress';
import { Alert, AlertDescription } from './ui/alert';

interface InitializationProgressProps {
  phase: 'auth' | 'websocket' | 'store' | 'ready' | 'error';
  progress: number;
  error?: string;
  connectionStatus?: 'CLOSED' | 'CONNECTING' | 'OPEN';
}

const phaseMessages = {
  auth: 'Authenticating your session...',
  websocket: 'Connecting to real-time services...',
  store: 'Loading your workspace...',
  ready: 'Ready!',
  error: 'Connection issue detected'
};

const phaseDetails = {
  auth: 'Verifying credentials and permissions',
  websocket: 'Establishing secure WebSocket connection',
  store: 'Synchronizing application state',
  ready: 'Initialization complete',
  error: 'Please check your connection and try again'
};

export function InitializationProgress({ 
  phase, 
  progress, 
  error,
  connectionStatus 
}: InitializationProgressProps) {
  const message = phaseMessages[phase];
  const detail = phaseDetails[phase];
  
  // Show connection status for WebSocket phase
  const showConnectionStatus = phase === 'websocket' && connectionStatus;
  
  return (
    <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-50">
      <div className="w-full max-w-md px-4">
        <div className="rounded-lg bg-white p-8 shadow-lg">
          {/* Logo or Brand */}
          <div className="mb-6 text-center">
            <h2 className="text-2xl font-semibold text-gray-900">Netra Apex</h2>
            <p className="mt-1 text-sm text-gray-600">AI Optimization Platform</p>
          </div>
          
          {/* Progress Bar */}
          <div className="mb-4">
            <Progress value={progress} className="h-2" />
          </div>
          
          {/* Status Message */}
          <div className="mb-4 text-center">
            <div className="flex items-center justify-center gap-2">
              {phase !== 'ready' && phase !== 'error' && (
                <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
              )}
              <p className="text-sm font-medium text-gray-900">{message}</p>
            </div>
            <p className="mt-1 text-xs text-gray-500">{detail}</p>
            
            {showConnectionStatus && (
              <p className="mt-2 text-xs text-gray-400">
                Status: {connectionStatus}
              </p>
            )}
          </div>
          
          {/* Phase Indicators */}
          <div className="flex justify-between px-2">
            <PhaseIndicator 
              label="Auth" 
              active={phase === 'auth'} 
              completed={progress > 33} 
            />
            <PhaseIndicator 
              label="Connect" 
              active={phase === 'websocket'} 
              completed={progress > 66} 
            />
            <PhaseIndicator 
              label="Load" 
              active={phase === 'store'} 
              completed={progress >= 100} 
            />
          </div>
          
          {/* Error Display */}
          {error && phase === 'error' && (
            <Alert variant="destructive" className="mt-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          {/* Progress Percentage */}
          <div className="mt-4 text-center">
            <span className="text-xs text-gray-400">{Math.round(progress)}% complete</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function PhaseIndicator({ 
  label, 
  active, 
  completed 
}: { 
  label: string; 
  active: boolean; 
  completed: boolean; 
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div 
        className={`
          h-2 w-2 rounded-full transition-all duration-300
          ${completed ? 'bg-green-500' : active ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'}
        `}
      />
      <span 
        className={`
          text-xs transition-colors duration-300
          ${active ? 'font-medium text-gray-900' : 'text-gray-500'}
        `}
      >
        {label}
      </span>
    </div>
  );
}