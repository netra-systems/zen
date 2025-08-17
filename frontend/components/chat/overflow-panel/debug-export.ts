export interface DebugExportOptions {
  currentRunId: string | null;
  activeThreadId: string | null;
  wsEventBuffer: any;
  executedAgents: Map<string, any>;
  performanceMetrics: any;
  messages: any[];
}

const createDebugData = (options: DebugExportOptions) => {
  return {
    timestamp: new Date().toISOString(),
    currentRunId: options.currentRunId,
    activeThreadId: options.activeThreadId,
    events: options.wsEventBuffer.exportAsJSON(),
    executedAgents: Array.from(options.executedAgents.entries()),
    performanceMetrics: options.performanceMetrics,
    messages: options.messages.slice(-20), // Last 20 messages
  };
};

const addSystemInfo = (debugData: any) => {
  return {
    ...debugData,
    userAgent: navigator.userAgent,
    bufferStats: debugData.wsEventBuffer?.getStats?.() || null,
  };
};

const createBlob = (data: any) => {
  return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
};

const createDownloadLink = (blob: Blob) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `netra-debug-${Date.now()}.json`;
  return { url, element: a };
};

const triggerDownload = (element: HTMLAnchorElement) => {
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
};

const cleanupUrl = (url: string) => {
  URL.revokeObjectURL(url);
};

export const exportDebugData = (options: DebugExportOptions): void => {
  const debugData = createDebugData(options);
  const enrichedData = addSystemInfo(debugData);
  const blob = createBlob(enrichedData);
  const { url, element } = createDownloadLink(blob);
  
  triggerDownload(element);
  cleanupUrl(url);
};