// Streaming utilities for content display
// Business Value: Optimized 30 chars/sec streaming for enhanced UX across all customer segments

export interface StreamingRefs {
  setDisplayedContent: (content: string) => void;
  setIsStreaming: (streaming: boolean) => void;
  contentRef: React.MutableRefObject<string>;
  animationFrameRef: React.MutableRefObject<number>;
  lastUpdateRef: React.MutableRefObject<number>;
}

// ============================================
// Main Streaming Handler (≤8 lines per function)
// ============================================

export const handleContentStreaming = (
  targetContent: string | undefined,
  refs: StreamingRefs
): (() => void) => {
  if (!targetContent) {
    resetStreamingState(refs);
    return () => {};
  }
  
  return initializeStreaming(targetContent, refs);
};

const resetStreamingState = (refs: StreamingRefs): void => {
  refs.setDisplayedContent('');
  refs.contentRef.current = '';
};

const initializeStreaming = (
  targetContent: string,
  refs: StreamingRefs
): (() => void) => {
  if (shouldSkipStreaming(targetContent, refs.contentRef)) {
    return () => {};
  }
  
  const cleanup = startStreamingProcess(targetContent, refs);
  return cleanup;
};

// ============================================
// Streaming Logic Functions
// ============================================

const shouldSkipStreaming = (
  targetContent: string,
  contentRef: React.MutableRefObject<string>
): boolean => {
  if (contentRef.current === targetContent) {
    return true;
  }
  
  if (!targetContent.startsWith(contentRef.current) && contentRef.current.length > 0) {
    contentRef.current = '';
  }
  
  return false;
};

const startStreamingProcess = (
  targetContent: string,
  refs: StreamingRefs
): (() => void) => {
  let currentIndex = refs.contentRef.current.length;
  refs.setIsStreaming(true);
  
  const config = getStreamingConfig();
  refs.lastUpdateRef.current = Date.now();
  
  const streamContent = createStreamingFunction(
    targetContent,
    refs,
    config,
    () => currentIndex,
    (newIndex) => { currentIndex = newIndex; }
  );
  
  refs.animationFrameRef.current = requestAnimationFrame(streamContent);
  return createCleanupFunction(refs);
};

const getStreamingConfig = () => ({
  charactersPerSecond: 30, // Spec requirement: 30 chars/sec
  msPerCharacter: 1000 / 30
});

// ============================================
// Animation Frame Functions
// ============================================

const createStreamingFunction = (
  targetContent: string,
  refs: StreamingRefs,
  config: { msPerCharacter: number },
  getCurrentIndex: () => number,
  setCurrentIndex: (index: number) => void
) => {
  const streamContent = (): void => {
    const { shouldContinue, newIndex } = processStreamingFrame(
      targetContent,
      refs,
      config,
      getCurrentIndex()
    );
    
    setCurrentIndex(newIndex);
    
    if (shouldContinue) {
      refs.animationFrameRef.current = requestAnimationFrame(streamContent);
    } else {
      refs.setIsStreaming(false);
    }
  };
  
  return streamContent;
};

const processStreamingFrame = (
  targetContent: string,
  refs: StreamingRefs,
  config: { msPerCharacter: number },
  currentIndex: number
): { shouldContinue: boolean; newIndex: number } => {
  const now = Date.now();
  const elapsed = now - refs.lastUpdateRef.current;
  
  if (elapsed >= config.msPerCharacter && currentIndex < targetContent.length) {
    const { newContent, endIndex } = calculateStreamingUpdate(
      targetContent,
      currentIndex,
      elapsed,
      config.msPerCharacter
    );
    
    updateStreamingState(refs, newContent, now);
    return { shouldContinue: endIndex < targetContent.length, newIndex: endIndex };
  }
  
  return { shouldContinue: currentIndex < targetContent.length, newIndex: currentIndex };
};

// ============================================
// Content Update Functions
// ============================================

const calculateStreamingUpdate = (
  targetContent: string,
  currentIndex: number,
  elapsed: number,
  msPerCharacter: number
): { newContent: string; endIndex: number } => {
  const charactersToAdd = Math.max(1, Math.floor(elapsed / msPerCharacter));
  const endIndex = Math.min(currentIndex + charactersToAdd, targetContent.length);
  const newContent = targetContent.substring(0, endIndex);
  
  return { newContent, endIndex };
};

const updateStreamingState = (
  refs: StreamingRefs,
  newContent: string,
  timestamp: number
): void => {
  refs.contentRef.current = newContent;
  refs.setDisplayedContent(newContent);
  refs.lastUpdateRef.current = timestamp;
};

const createCleanupFunction = (refs: StreamingRefs): (() => void) => {
  return () => {
    if (refs.animationFrameRef.current) {
      cancelAnimationFrame(refs.animationFrameRef.current);
    }
  };
};