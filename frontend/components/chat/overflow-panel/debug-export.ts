export interface DebugExportOptions {
  currentRunId: string | null;
  activeThreadId: string | null;
  wsEventBuffer: any[];
  executedAgents: any[];
  performanceMetrics: any;
  messages: any[];
}

export function exportDebugData(options: DebugExportOptions): void {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `netra-debug-${timestamp}.json`;
  
  const debugData = {
    exportedAt: new Date().toISOString(),
    runId: options.currentRunId,
    threadId: options.activeThreadId,
    events: options.wsEventBuffer,
    agents: options.executedAgents,
    metrics: options.performanceMetrics,
    messages: options.messages.map(msg => ({
      id: msg.id,
      role: msg.role,
      content: msg.content.substring(0, 500),
      timestamp: msg.timestamp
    }))
  };

  const blob = new Blob([JSON.stringify(debugData, null, 2)], { 
    type: 'application/json' 
  });
  
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
}