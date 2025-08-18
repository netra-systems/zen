/**
 * Event Diagnostics Panel Component
 * 
 * Extracted from MainChat.tsx to maintain 300-line file limit
 * Provides real-time diagnostics for WebSocket event processing
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed React component
 */

import React from 'react';
import { runEventQueueTests } from '@/lib/event-queue.test';
import { websocketDebugger } from '@/services/websocketDebugger';
import { logger } from '@/utils/debug-logger';

// ============================================
// Helper Functions (8 lines max each)
// ============================================

const handleTestExecution = async (
  setIsRunningTests: (running: boolean) => void,
  setTestResults: (results: any) => void
): Promise<void> => {
  setIsRunningTests(true);
  try {
    const results = await runEventQueueTests();
    setTestResults(results);
    logger.debug('Event Queue Test Results:', results);
  } catch (error) {
    handleTestError(error, setTestResults);
  } finally {
    setIsRunningTests(false);
  }
};

const handleTestError = (error: unknown, setTestResults: (results: any) => void): void => {
  logger.error('Test execution failed:', error);
  setTestResults({ error: (error as Error).message });
};

const handleDebugReportGeneration = (): void => {
  const report = websocketDebugger.generateDebugReport();
  logger.debug('WebSocket Debug Report:\n', report);
  navigator.clipboard.writeText(report).catch(() => {});
};

const renderWebSocketStats = () => {
  const debugStats = websocketDebugger.getStats();
  return (
    <>
      <div>Health Score: {debugStats.healthScore}/100</div>
      <div>Avg Latency: {debugStats.averageProcessingTime.toFixed(1)}ms</div>
      <div>Failed Events: {debugStats.failedEvents.length}</div>
    </>
  );
};

const renderTestResultsError = (error: string) => (
  <div className="text-xs text-red-600">Error: {error}</div>
);

const renderTestResultsSuccess = (testResults: any) => (
  <div className="text-xs space-y-1">
    <div>Tests: {testResults.passedTests}/{testResults.totalTests}</div>
    <div className={testResults.success ? 'text-green-600' : 'text-red-600'}>
      {testResults.success ? '✅ All Passed' : '❌ Some Failed'}
    </div>
    {renderTestResultsDetails(testResults)}
  </div>
);

const renderTestResultsDetails = (testResults: any) => (
  <details className="mt-2">
    <summary className="cursor-pointer">Details</summary>
    <div className="mt-1 text-xs space-y-1">
      {testResults.results?.map((result: any, index: number) => (
        <div key={index} className={result.success ? 'text-green-600' : 'text-red-600'}>
          {result.success ? '✅' : '❌'} {result.testName}
        </div>
      ))}
    </div>
  </details>
);

// ============================================
// Component Props Interface
// ============================================

interface EventDiagnosticsPanelProps {
  showEventDiagnostics: boolean;
  setShowEventDiagnostics: (show: boolean) => void;
  eventProcessor: {
    processedCount: number;
    errorCount: number;
    queueSize: number;
    duplicatesDropped: number;
    clearQueue: () => void;
  };
  wsMessages: any[];
  testResults: any;
  setTestResults: (results: any) => void;
  isRunningTests: boolean;
  setIsRunningTests: (running: boolean) => void;
}

// ============================================
// Main Component
// ============================================

export const EventDiagnosticsPanel: React.FC<EventDiagnosticsPanelProps> = ({
  showEventDiagnostics,
  setShowEventDiagnostics,
  eventProcessor,
  wsMessages,
  testResults,
  setTestResults,
  isRunningTests,
  setIsRunningTests
}) => {
  const runTests = async () => {
    await handleTestExecution(setIsRunningTests, setTestResults);
  };

  if (!showEventDiagnostics) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white shadow-lg rounded-lg p-4 border max-w-sm z-50 max-h-96 overflow-y-auto">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-semibold text-sm">Event Processing</h3>
        <button 
          onClick={() => setShowEventDiagnostics(false)}
          className="text-gray-500 hover:text-gray-700"
        >
          ×
        </button>
      </div>
      
      {/* Current Stats */}
      <div className="text-xs space-y-1 mb-3">
        <div>Processed: {eventProcessor.processedCount}</div>
        <div>Errors: {eventProcessor.errorCount}</div>
        <div>Queue Size: {eventProcessor.queueSize}</div>
        <div>Duplicates Dropped: {eventProcessor.duplicatesDropped}</div>
        <div>Total WS Messages: {wsMessages.length}</div>
        
        {/* WebSocket Debugger Stats */}
        <div className="border-t pt-2 mt-2">
          <div className="font-medium">WebSocket Health:</div>
          {renderWebSocketStats()}
        </div>
      </div>
      
      {/* Action Buttons */}
      <div className="space-y-2 mb-3">
        <button 
          onClick={eventProcessor.clearQueue}
          className="text-xs bg-red-100 hover:bg-red-200 px-2 py-1 rounded w-full"
        >
          Clear Queue
        </button>
        <button 
          onClick={runTests}
          disabled={isRunningTests}
          className="text-xs bg-blue-100 hover:bg-blue-200 disabled:bg-gray-100 px-2 py-1 rounded w-full"
        >
          {isRunningTests ? 'Running Tests...' : 'Run Queue Tests'}
        </button>
        <button 
          onClick={() => websocketDebugger.setDebugMode(!websocketDebugger.getStats().healthScore)}
          className="text-xs bg-green-100 hover:bg-green-200 px-2 py-1 rounded w-full"
        >
          Toggle Debug Mode
        </button>
        <button 
          onClick={handleDebugReportGeneration}
          className="text-xs bg-purple-100 hover:bg-purple-200 px-2 py-1 rounded w-full"
        >
          Generate Debug Report
        </button>
      </div>
      
      {/* Test Results */}
      {testResults && (
        <div className="border-t pt-2">
          <h4 className="text-xs font-semibold mb-1">Test Results</h4>
          {testResults.error ? 
            renderTestResultsError(testResults.error) :
            renderTestResultsSuccess(testResults)
          }
        </div>
      )}
      
      <div className="text-xs text-gray-500 mt-2 border-t pt-2">
        Ctrl+Shift+E to toggle
      </div>
    </div>
  );
};

EventDiagnosticsPanel.displayName = 'EventDiagnosticsPanel';