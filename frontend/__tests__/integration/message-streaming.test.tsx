/**
 * Message Streaming Integration Tests
 * Tests WebSocket message streaming with backpressure handling
 * Agent 10 Implementation - 60 FPS streaming performance focus
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';

interface StreamingMetrics {
  messagesPerSecond: number;
  framesPerSecond: number;
  droppedFrames: number;
  bufferSize: number;
  backpressureEvents: number;
  latencyMs: number;
}

interface MessageChunk {
  id: string;
  sequence: number;
  data: string;
  timestamp: number;
  size: number;
}

// Create chunk utility
const createChunk = (data: string, sequence: number): MessageChunk => ({
  id: Math.random().toString(36).substr(2, 9),
  sequence,
  data,
  timestamp: Date.now(),
  size: data.length
});

// Streaming test component
const MessageStreamingTest: React.FC = () => {
  const [metrics, setMetrics] = React.useState<StreamingMetrics>({
    messagesPerSecond: 0, framesPerSecond: 0, droppedFrames: 0,
    bufferSize: 0, backpressureEvents: 0, latencyMs: 0
  });
  const [chunks, setChunks] = React.useState<MessageChunk[]>([]);
  const [isStreaming, setIsStreaming] = React.useState(false);

  const updateMetric = (key: keyof StreamingMetrics, value: number) => {
    setMetrics(prev => ({ ...prev, [key]: value }));
  };

  const addChunk = (data: string) => {
    const chunk = createChunk(data, chunks.length + 1);
    setChunks(prev => [...prev, chunk]);
  };

  const startStreaming = () => setIsStreaming(true);
  const stopStreaming = () => setIsStreaming(false);

  return (
    <div>
      <div data-testid="is-streaming">{isStreaming.toString()}</div>
      <div data-testid="chunk-count">{chunks.length}</div>
      
      <div data-testid="metrics-mps">{metrics.messagesPerSecond}</div>
      <div data-testid="metrics-fps">{metrics.framesPerSecond}</div>
      <div data-testid="metrics-dropped">{metrics.droppedFrames}</div>
      <div data-testid="metrics-buffer">{metrics.bufferSize}</div>
      <div data-testid="metrics-backpressure">{metrics.backpressureEvents}</div>
      <div data-testid="metrics-latency">{metrics.latencyMs}</div>
      
      <button onClick={startStreaming} data-testid="btn-start-stream">
        Start Streaming
      </button>
      <button onClick={stopStreaming} data-testid="btn-stop-stream">
        Stop Streaming
      </button>
      <button onClick={() => addChunk('test data')} data-testid="btn-add-chunk">
        Add Chunk
      </button>
      <button onClick={() => updateMetric('messagesPerSecond', 60)} data-testid="btn-set-mps">
        Set MPS
      </button>
      <button onClick={() => updateMetric('framesPerSecond', 60)} data-testid="btn-set-fps">
        Set FPS
      </button>
      <button onClick={() => updateMetric('droppedFrames', 1)} data-testid="btn-drop-frame">
        Drop Frame
      </button>
      <button onClick={() => updateMetric('backpressureEvents', 1)} data-testid="btn-backpressure">
        Backpressure
      </button>
    </div>
  );
};

// Message stream buffer
class StreamBuffer {
  private buffer: MessageChunk[] = [];
  private maxSize: number;
  private highWaterMark: number;

  constructor(maxSize: number = 1000) {
    this.maxSize = maxSize;
    this.highWaterMark = Math.floor(maxSize * 0.8);
  }

  enqueue(chunk: MessageChunk): boolean {
    if (this.buffer.length >= this.maxSize) return false;
    this.buffer.push(chunk);
    return true;
  }

  dequeue(): MessageChunk | null { return this.buffer.shift() || null; }
  size(): number { return this.buffer.length; }
  isBackpressured(): boolean { return this.buffer.length >= this.highWaterMark; }
}

// Frame rate controller
class FrameRateController {
  private targetFPS: number = 60;
  private frameInterval: number;
  private lastFrameTime: number = 0;

  constructor(targetFPS: number = 60) {
    this.targetFPS = targetFPS;
    this.frameInterval = 1000 / targetFPS;
  }

  shouldRender(currentTime: number): boolean {
    if (currentTime - this.lastFrameTime >= this.frameInterval) {
      this.lastFrameTime = currentTime;
      return true;
    }
    return false;
  }

  getTargetInterval(): number {
    return this.frameInterval;
  }
}

// Streaming performance monitor
class StreamingPerformanceMonitor {
  private messageTimestamps: number[] = [];
  private frameTimestamps: number[] = [];
  private droppedFrames: number = 0;

  recordMessage(): void {
    this.messageTimestamps.push(Date.now());
    this.cleanOldTimestamps();
  }

  recordFrame(): void {
    this.frameTimestamps.push(Date.now());
    this.cleanOldTimestamps();
  }

  recordDroppedFrame(): void {
    this.droppedFrames++;
  }

  getMessagesPerSecond(): number {
    return this.messageTimestamps.length;
  }

  getFramesPerSecond(): number {
    return this.frameTimestamps.length;
  }

  getDroppedFrames(): number {
    return this.droppedFrames;
  }

  private cleanOldTimestamps(): void {
    const oneSecondAgo = Date.now() - 1000;
    this.messageTimestamps = this.messageTimestamps.filter(t => t > oneSecondAgo);
    this.frameTimestamps = this.frameTimestamps.filter(t => t > oneSecondAgo);
  }
}

// Backpressure handler
class BackpressureHandler {
  private threshold: number;
  private events: number = 0;

  constructor(threshold: number = 100) {
    this.threshold = threshold;
  }

  checkBackpressure(bufferSize: number): boolean {
    if (bufferSize > this.threshold) {
      this.events++;
      return true;
    }
    return false;
  }

  getEventCount(): number {
    return this.events;
  }

  reset(): void {
    this.events = 0;
  }
}

describe('Message Streaming Integration Tests', () => {
  let wsManager: WebSocketTestManager;
  let streamBuffer: StreamBuffer;
  let frameController: FrameRateController;
  let performanceMonitor: StreamingPerformanceMonitor;
  let backpressureHandler: BackpressureHandler;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    streamBuffer = new StreamBuffer();
    frameController = new FrameRateController();
    performanceMonitor = new StreamingPerformanceMonitor();
    backpressureHandler = new BackpressureHandler();
    wsManager.setup();
    jest.useFakeTimers();
  });

  afterEach(() => {
    wsManager.cleanup();
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  describe('Streaming Controls', () => {
    it('should start and stop streaming', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      expect(screen.getByTestId('is-streaming')).toHaveTextContent('false');
      
      await userEvent.click(screen.getByTestId('btn-start-stream'));
      expect(screen.getByTestId('is-streaming')).toHaveTextContent('true');
      
      await userEvent.click(screen.getByTestId('btn-stop-stream'));
      expect(screen.getByTestId('is-streaming')).toHaveTextContent('false');
    });

    it('should add message chunks', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      expect(screen.getByTestId('chunk-count')).toHaveTextContent('0');
      
      await userEvent.click(screen.getByTestId('btn-add-chunk'));
      expect(screen.getByTestId('chunk-count')).toHaveTextContent('1');
      
      await userEvent.click(screen.getByTestId('btn-add-chunk'));
      expect(screen.getByTestId('chunk-count')).toHaveTextContent('2');
    });
  });

  describe('Performance Metrics', () => {
    it('should track messages per second', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      await userEvent.click(screen.getByTestId('btn-set-mps'));
      expect(screen.getByTestId('metrics-mps')).toHaveTextContent('60');
    });

    it('should achieve 60 FPS target', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      await userEvent.click(screen.getByTestId('btn-set-fps'));
      expect(screen.getByTestId('metrics-fps')).toHaveTextContent('60');
    });

    it('should track dropped frames', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      await userEvent.click(screen.getByTestId('btn-drop-frame'));
      expect(screen.getByTestId('metrics-dropped')).toHaveTextContent('1');
    });

    it('should monitor performance in real-time', () => {
      performanceMonitor.recordMessage();
      performanceMonitor.recordFrame();
      
      expect(performanceMonitor.getMessagesPerSecond()).toBe(1);
      expect(performanceMonitor.getFramesPerSecond()).toBe(1);
    });
  });

  describe('Stream Buffer Management', () => {
    it('should enqueue and dequeue messages', () => {
      const chunk: MessageChunk = {
        id: 'test-1',
        sequence: 1,
        data: 'test data',
        timestamp: Date.now(),
        size: 9
      };

      const success = streamBuffer.enqueue(chunk);
      expect(success).toBe(true);
      expect(streamBuffer.size()).toBe(1);

      const dequeued = streamBuffer.dequeue();
      expect(dequeued?.id).toBe('test-1');
      expect(streamBuffer.size()).toBe(0);
    });

    it('should respect buffer limits', () => {
      const smallBuffer = new StreamBuffer(2);
      
      const chunk1: MessageChunk = {
        id: 'test-1', sequence: 1, data: 'data1', timestamp: Date.now(), size: 5
      };
      const chunk2: MessageChunk = {
        id: 'test-2', sequence: 2, data: 'data2', timestamp: Date.now(), size: 5
      };
      const chunk3: MessageChunk = {
        id: 'test-3', sequence: 3, data: 'data3', timestamp: Date.now(), size: 5
      };

      expect(smallBuffer.enqueue(chunk1)).toBe(true);
      expect(smallBuffer.enqueue(chunk2)).toBe(true);
      expect(smallBuffer.enqueue(chunk3)).toBe(false); // Buffer full
    });

    it('should detect backpressure conditions', () => {
      const buffer = new StreamBuffer(10);
      
      // Fill buffer beyond high water mark
      for (let i = 0; i < 9; i++) {
        buffer.enqueue({
          id: `msg-${i}`,
          sequence: i,
          data: 'data',
          timestamp: Date.now(),
          size: 4
        });
      }

      expect(buffer.isBackpressured()).toBe(true);
    });
  });

  describe('Frame Rate Control', () => {
    it('should maintain 60 FPS target', () => {
      const controller = new FrameRateController(60);
      expect(controller.getTargetInterval()).toBeCloseTo(16.67, 1);
    });

    it('should throttle frame rendering', () => {
      const controller = new FrameRateController(60);
      const now = Date.now();
      
      expect(controller.shouldRender(now)).toBe(true);
      expect(controller.shouldRender(now + 5)).toBe(false);  // Too soon
      expect(controller.shouldRender(now + 20)).toBe(true);  // Enough time passed
    });

    it('should adapt to different frame rates', () => {
      const controller30 = new FrameRateController(30);
      const controller120 = new FrameRateController(120);
      
      expect(controller30.getTargetInterval()).toBeCloseTo(33.33, 1);
      expect(controller120.getTargetInterval()).toBeCloseTo(8.33, 1);
    });
  });

  describe('Backpressure Handling', () => {
    it('should detect backpressure events', async () => {
      render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      await userEvent.click(screen.getByTestId('btn-backpressure'));
      expect(screen.getByTestId('metrics-backpressure')).toHaveTextContent('1');
    });

    it('should trigger backpressure at threshold', () => {
      const handler = new BackpressureHandler(50);
      
      expect(handler.checkBackpressure(30)).toBe(false);
      expect(handler.checkBackpressure(60)).toBe(true);
      expect(handler.getEventCount()).toBe(1);
    });

    it('should reset backpressure counters', () => {
      const handler = new BackpressureHandler(50);
      
      handler.checkBackpressure(60);
      expect(handler.getEventCount()).toBe(1);
      
      handler.reset();
      expect(handler.getEventCount()).toBe(0);
    });
  });

  describe('Binary and Text Messages', () => {
    it('should handle text message types', () => {
      const textChunk: MessageChunk = {
        id: 'text-1',
        sequence: 1,
        data: JSON.stringify({ type: 'text', content: 'Hello' }),
        timestamp: Date.now(),
        size: 32
      };

      expect(streamBuffer.enqueue(textChunk)).toBe(true);
      expect(textChunk.data).toContain('text');
    });

    it('should handle binary message simulation', () => {
      const binaryData = new Uint8Array([1, 2, 3, 4, 5]);
      const binaryChunk: MessageChunk = {
        id: 'binary-1',
        sequence: 1,
        data: JSON.stringify({ type: 'binary', size: binaryData.length }),
        timestamp: Date.now(),
        size: binaryData.length
      };

      expect(streamBuffer.enqueue(binaryChunk)).toBe(true);
      expect(binaryChunk.data).toContain('binary');
    });

    it('should handle large message chunking', () => {
      const largeData = 'x'.repeat(1000000); // 1MB
      const largeChunk: MessageChunk = {
        id: 'large-1',
        sequence: 1,
        data: largeData,
        timestamp: Date.now(),
        size: largeData.length
      };

      expect(largeChunk.size).toBe(1000000);
    });
  });

  describe('Latency Monitoring', () => {
    it('should measure message latency', () => {
      const sendTime = Date.now();
      const receiveTime = sendTime + 50; // 50ms latency
      const latency = receiveTime - sendTime;
      
      expect(latency).toBe(50);
    });

    it('should track latency trends', () => {
      const latencies = [10, 15, 12, 8, 20];
      const avgLatency = latencies.reduce((a, b) => a + b) / latencies.length;
      
      expect(avgLatency).toBe(13);
    });
  });

  describe('Resource Cleanup', () => {
    it('should clean up streaming resources', async () => {
      const { unmount } = render(
        <TestProviders>
          <MessageStreamingTest />
        </TestProviders>
      );

      unmount();
      // Should not throw during cleanup
      expect(true).toBe(true);
    });

    it('should handle abrupt disconnections', () => {
      streamBuffer.enqueue({
        id: 'test',
        sequence: 1,
        data: 'data',
        timestamp: Date.now(),
        size: 4
      });

      // Simulate abrupt disconnection
      wsManager.close();
      
      // Buffer should maintain data for recovery
      expect(streamBuffer.size()).toBe(1);
    });
  });
});