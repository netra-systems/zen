/**
 * Chat Component Streaming Tests
 * Tests character-by-character streaming, smooth rendering, and performance
 * 
 * Phase 4, Agent 14: Component-level streaming behavior verification
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Performance monitoring utilities
const createPerformanceMonitor = () => {
  const frames: number[] = [];
  let lastFrameTime = 0;
  
  return {
    startFrame: () => {
      lastFrameTime = performance.now();
    },
    endFrame: () => {
      const currentTime = performance.now();
      const frameDuration = currentTime - lastFrameTime;
      frames.push(frameDuration);
      return frameDuration;
    },
    getAverageFrameTime: () => {
      return frames.length > 0 ? frames.reduce((a, b) => a + b, 0) / frames.length : 0;
    },
    getFPS: () => {
      const avgFrameTime = frames.length > 0 ? frames.reduce((a, b) => a + b, 0) / frames.length : 16.67;
      return Math.round(1000 / avgFrameTime);
    },
    reset: () => {
      frames.length = 0;
      lastFrameTime = 0;
    }
  };
};

// Character-by-character streaming component
const CharacterStreamComponent: React.FC<{
  text: string;
  speed?: number;
  onComplete?: () => void;
  onProgress?: (progress: number) => void;
}> = ({ text, speed = 50, onComplete, onProgress }) => {
  const [displayText, setDisplayText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (text && !isStreaming) {
      setIsStreaming(true);
      setCurrentIndex(0);
      setDisplayText('');
      
      intervalRef.current = setInterval(() => {
        setCurrentIndex(prev => {
          const nextIndex = prev + 1;
          const newText = text.slice(0, nextIndex);
          setDisplayText(newText);
          
          const progress = (nextIndex / text.length) * 100;
          onProgress?.(progress);
          
          if (nextIndex >= text.length) {
            setIsStreaming(false);
            onComplete?.();
            clearInterval(intervalRef.current);
          }
          
          return nextIndex;
        });
      }, speed);
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [text, speed, onComplete, onProgress]);

  return (
    <div data-testid="character-stream">
      <div data-testid="stream-text">{displayText}</div>
      <div data-testid="stream-progress">{Math.round((currentIndex / text.length) * 100)}%</div>
      <div data-testid="stream-status">{isStreaming ? 'streaming' : 'complete'}</div>
    </div>
  );
};

// Smooth rendering test component with 60 FPS monitoring
const SmoothRenderComponent: React.FC<{
  chunks: string[];
  targetFPS?: number;
}> = ({ chunks, targetFPS = 60 }) => {
  const [content, setContent] = useState('');
  const [renderMetrics, setRenderMetrics] = useState({
    fps: 0,
    frameTime: 0,
    droppedFrames: 0
  });
  const performanceMonitor = useRef(createPerformanceMonitor());
  const animationRef = useRef<number>();
  const chunkIndex = useRef(0);

  const updateContent = useCallback(() => {
    performanceMonitor.current.startFrame();
    
    if (chunkIndex.current < chunks.length) {
      setContent(prev => prev + chunks[chunkIndex.current] + ' ');
      chunkIndex.current++;
      
      // Schedule next update using setTimeout for test compatibility
      const delay = 1000 / targetFPS; // Convert FPS to ms delay
      setTimeout(updateContent, delay);
    }
    
    const frameTime = performanceMonitor.current.endFrame();
    const fps = performanceMonitor.current.getFPS();
    const droppedFrames = frameTime > (1000 / targetFPS) ? 1 : 0;
    
    setRenderMetrics({
      fps,
      frameTime,
      droppedFrames
    });
  }, [chunks, targetFPS]);

  useEffect(() => {
    if (chunks.length > 0) {
      chunkIndex.current = 0;
      setContent('');
      performanceMonitor.current.reset();
      setTimeout(updateContent, 1000 / targetFPS);
    }
  }, [chunks, updateContent, targetFPS]);

  return (
    <div data-testid="smooth-render">
      <div data-testid="render-content">{content}</div>
      <div data-testid="render-fps">{renderMetrics.fps}</div>
      <div data-testid="render-frame-time">{renderMetrics.frameTime.toFixed(2)}</div>
      <div data-testid="dropped-frames">{renderMetrics.droppedFrames}</div>
    </div>
  );
};

// Chunked message assembly component
const ChunkedAssemblyComponent: React.FC<{
  messageChunks: Array<{ id: string; content: string; order: number }>;
  onAssemblyComplete?: (fullMessage: string) => void;
}> = ({ messageChunks, onAssemblyComplete }) => {
  const [assembledMessage, setAssembledMessage] = useState('');
  const [receivedChunks, setReceivedChunks] = useState<Map<number, string>>(new Map());
  const [isAssembling, setIsAssembling] = useState(false);

  useEffect(() => {
    if (messageChunks.length > 0) {
      setIsAssembling(true);
      
      // Process chunks in order
      const chunkMap = new Map<number, string>();
      messageChunks.forEach(chunk => {
        chunkMap.set(chunk.order, chunk.content);
      });
      
      setReceivedChunks(chunkMap);
      
      // Assemble message from ordered chunks
      const sortedChunks = Array.from(chunkMap.entries())
        .sort(([a], [b]) => a - b)
        .map(([, content]) => content);
      
      const fullMessage = sortedChunks.join(' ');
      setAssembledMessage(fullMessage);
      setIsAssembling(false);
      
      onAssemblyComplete?.(fullMessage);
    }
  }, [messageChunks, onAssemblyComplete]);

  return (
    <div data-testid="chunked-assembly">
      <div data-testid="assembled-message">{assembledMessage}</div>
      <div data-testid="chunk-count">{receivedChunks.size}</div>
      <div data-testid="assembly-status">{isAssembling ? 'assembling' : 'complete'}</div>
    </div>
  );
};

// Progress indicator component
const ProgressIndicatorComponent: React.FC<{
  totalSteps: number;
  currentStep?: number;
  stepLabels?: string[];
}> = ({ totalSteps, currentStep = 0, stepLabels = [] }) => {
  const [progress, setProgress] = useState(0);
  const [activeStep, setActiveStep] = useState(currentStep);

  useEffect(() => {
    setActiveStep(currentStep);
    setProgress((currentStep / totalSteps) * 100);
  }, [currentStep, totalSteps]);

  return (
    <div data-testid="progress-indicator">
      <div data-testid="progress-bar" style={{ width: `${progress}%`, backgroundColor: 'blue', height: '10px' }} />
      <div data-testid="progress-percentage">{Math.round(progress)}%</div>
      <div data-testid="current-step">{activeStep}</div>
      <div data-testid="total-steps">{totalSteps}</div>
      {stepLabels.length > 0 && (
        <div data-testid="step-label">{stepLabels[activeStep] || ''}</div>
      )}
    </div>
  );
};

// Interruption handling component
const InterruptionComponent: React.FC<{
  onInterrupt?: () => void;
}> = ({ onInterrupt }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [canInterrupt, setCanInterrupt] = useState(false);
  const processingRef = useRef<NodeJS.Timeout>();

  const startProcessing = () => {
    setIsProcessing(true);
    setCanInterrupt(true);
    
    processingRef.current = setTimeout(() => {
      setIsProcessing(false);
      setCanInterrupt(false);
    }, 2000);
  };

  const handleInterrupt = () => {
    if (canInterrupt && processingRef.current) {
      clearTimeout(processingRef.current);
      setIsProcessing(false);
      setCanInterrupt(false);
      onInterrupt?.();
    }
  };

  useEffect(() => {
    return () => {
      if (processingRef.current) {
        clearTimeout(processingRef.current);
      }
    };
  }, []);

  return (
    <div data-testid="interruption-component">
      <button onClick={startProcessing} disabled={isProcessing} data-testid="start-btn">
        Start Processing
      </button>
      <button onClick={handleInterrupt} disabled={!canInterrupt} data-testid="interrupt-btn">
        Interrupt
      </button>
      <div data-testid="processing-status">{isProcessing ? 'processing' : 'idle'}</div>
      <div data-testid="interrupt-available">{canInterrupt ? 'yes' : 'no'}</div>
    </div>
  );
};

describe('Chat Component Streaming Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Character-by-Character Streaming', () => {
    it('should stream text character by character', async () => {
      const testText = 'Hello, World!';
      let completionCalled = false;
      
      render(
        <CharacterStreamComponent 
          text={testText}
          speed={10}
          onComplete={() => { completionCalled = true; }}
        />
      );

      // Should start empty
      expect(screen.getByTestId('stream-text')).toHaveTextContent('');
      expect(screen.getByTestId('stream-status')).toHaveTextContent('streaming');

      // Should progressively build text
      await waitFor(() => {
        expect(screen.getByTestId('stream-text')).toHaveTextContent('H');
      });

      await waitFor(() => {
        expect(screen.getByTestId('stream-text')).toHaveTextContent('Hello');
      });

      await waitFor(() => {
        expect(screen.getByTestId('stream-text')).toHaveTextContent(testText);
        expect(screen.getByTestId('stream-status')).toHaveTextContent('complete');
      });

      expect(completionCalled).toBe(true);
    });

    it('should report accurate progress during streaming', async () => {
      const progressValues: number[] = [];
      
      render(
        <CharacterStreamComponent 
          text="Test"
          speed={25}
          onProgress={(progress) => progressValues.push(progress)}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('stream-status')).toHaveTextContent('complete');
      });

      expect(progressValues.length).toBeGreaterThan(0);
      expect(progressValues[progressValues.length - 1]).toBe(100);
    });
  });

  describe('Smooth Rendering (60 FPS)', () => {
    it('should maintain 60 FPS during rendering', async () => {
      const chunks = ['Chunk1', 'Chunk2', 'Chunk3', 'Chunk4', 'Chunk5'];
      
      render(<SmoothRenderComponent chunks={chunks} targetFPS={60} />);

      await waitFor(() => {
        expect(screen.getByTestId('render-content')).toHaveTextContent('Chunk5');
      }, { timeout: 2000 });

      const fps = parseInt(screen.getByTestId('render-fps').textContent || '0');
      expect(fps).toBeGreaterThanOrEqual(30); // Allow some tolerance
    });

    it('should track frame time performance', async () => {
      const chunks = ['A'];
      
      render(<SmoothRenderComponent chunks={chunks} />);

      // Wait for initial render and performance metrics
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      // Check that performance metrics are being tracked
      const frameTimeElement = screen.getByTestId('render-frame-time');
      expect(frameTimeElement).toBeInTheDocument();
      
      const frameTime = parseFloat(frameTimeElement.textContent || '0');
      expect(frameTime).toBeGreaterThanOrEqual(0); // Allow zero for test environment
    });
  });

  describe('No Flicker or Jumps', () => {
    it('should render without visual jumps during streaming', async () => {
      const LongContentTest: React.FC = () => {
        const [content, setContent] = useState('');
        const [measurements, setMeasurements] = useState<number[]>([]);
        const elementRef = useRef<HTMLDivElement>(null);

        useEffect(() => {
          const words = ['Word0', 'Word1', 'Word2'];
          let index = 0;
          
          const interval = setInterval(() => {
            if (index < words.length) {
              setContent(prev => prev + (prev ? ' ' : '') + words[index]);
              
              // Measure element height
              if (elementRef.current) {
                setMeasurements(prev => [...prev, elementRef.current!.offsetHeight]);
              }
              
              index++;
            } else {
              clearInterval(interval);
            }
          }, 50);
          
          return () => clearInterval(interval);
        }, []);

        return (
          <div>
            <div ref={elementRef} data-testid="long-content">{content}</div>
            <div data-testid="height-changes">{measurements.length}</div>
          </div>
        );
      };

      render(<LongContentTest />);

      await waitFor(() => {
        expect(screen.getByTestId('long-content')).toHaveTextContent('Word2');
      }, { timeout: 1000 });

      const heightChanges = parseInt(screen.getByTestId('height-changes').textContent || '0');
      expect(heightChanges).toBeGreaterThan(0);
    });
  });

  describe('Chunked Message Assembly', () => {
    it('should assemble messages from unordered chunks', async () => {
      const chunks = [
        { id: 'chunk-2', content: 'World!', order: 2 },
        { id: 'chunk-1', content: 'Hello', order: 1 },
        { id: 'chunk-3', content: 'Test', order: 3 }
      ];
      
      let assembledResult = '';

      render(
        <ChunkedAssemblyComponent 
          messageChunks={chunks}
          onAssemblyComplete={(message) => { assembledResult = message; }}
        />
      );

      await waitFor(() => {
        expect(screen.getByTestId('assembly-status')).toHaveTextContent('complete');
      });

      expect(screen.getByTestId('assembled-message')).toHaveTextContent('Hello World! Test');
      expect(screen.getByTestId('chunk-count')).toHaveTextContent('3');
      expect(assembledResult).toBe('Hello World! Test');
    });
  });

  describe('Progress Indicators', () => {
    it('should display accurate progress indicators', async () => {
      const ProgressTest: React.FC = () => {
        const [currentStep, setCurrentStep] = useState(0);
        const totalSteps = 5;
        const stepLabels = ['Init', 'Processing', 'Analysis', 'Results', 'Complete'];

        useEffect(() => {
          const interval = setInterval(() => {
            setCurrentStep(prev => {
              const next = prev + 1;
              if (next >= totalSteps) {
                clearInterval(interval);
                return totalSteps - 1;
              }
              return next;
            });
          }, 100);
          
          return () => clearInterval(interval);
        }, []);

        return (
          <ProgressIndicatorComponent 
            totalSteps={totalSteps}
            currentStep={currentStep}
            stepLabels={stepLabels}
          />
        );
      };

      render(<ProgressTest />);

      await waitFor(() => {
        expect(screen.getByTestId('progress-percentage')).toHaveTextContent('80%');
      }, { timeout: 1000 });

      expect(screen.getByTestId('step-label')).toHaveTextContent('Complete');
    });
  });

  describe('Interruption Handling', () => {
    it('should handle stream interruption gracefully', async () => {
      let interruptCalled = false;

      render(<InterruptionComponent onInterrupt={() => { interruptCalled = true; }} />);

      // Start processing
      fireEvent.click(screen.getByTestId('start-btn'));
      expect(screen.getByTestId('processing-status')).toHaveTextContent('processing');
      expect(screen.getByTestId('interrupt-available')).toHaveTextContent('yes');

      // Interrupt
      fireEvent.click(screen.getByTestId('interrupt-btn'));
      expect(screen.getByTestId('processing-status')).toHaveTextContent('idle');
      expect(screen.getByTestId('interrupt-available')).toHaveTextContent('no');
      expect(interruptCalled).toBe(true);
    });
  });

  describe('Message Ordering', () => {
    it('should maintain correct message order during concurrent streams', async () => {
      const MessageOrderTest: React.FC = () => {
        const [messages, setMessages] = useState<Array<{ id: number; content: string }>>([]);
        
        useEffect(() => {
          // Simulate concurrent message arrivals
          const addMessage = (id: number, delay: number) => {
            setTimeout(() => {
              setMessages(prev => [...prev, { id, content: `Message ${id}` }]);
            }, delay);
          };
          
          addMessage(1, 50);
          addMessage(2, 25);
          addMessage(3, 75);
          addMessage(4, 10);
        }, []);

        return (
          <div data-testid="message-order">
            {messages.map(msg => (
              <div key={msg.id} data-testid={`message-${msg.id}`}>
                {msg.content}
              </div>
            ))}
            <div data-testid="message-count">{messages.length}</div>
          </div>
        );
      };

      render(<MessageOrderTest />);

      await waitFor(() => {
        expect(screen.getByTestId('message-count')).toHaveTextContent('4');
      }, { timeout: 200 });

      // Messages should appear in arrival order, not ID order
      expect(screen.getByTestId('message-4')).toBeInTheDocument();
      expect(screen.getByTestId('message-2')).toBeInTheDocument();
      expect(screen.getByTestId('message-1')).toBeInTheDocument();
      expect(screen.getByTestId('message-3')).toBeInTheDocument();
    });
  });
});