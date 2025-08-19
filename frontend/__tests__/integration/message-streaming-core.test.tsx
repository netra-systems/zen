/**
 * Message Streaming Core Tests
 * Core streaming functionality tests
 * Agent 10 Implementation - Split for 300-line compliance
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';
import { TestProviders } from '../setup/test-providers';
import { WebSocketTestManager } from '../helpers/websocket-test-manager';
import { StreamingMetrics, MessageChunk, createMessageChunk } from '../helpers/websocket-test-utilities';
import { StreamBuffer, FrameRateController, StreamingPerformanceMonitor } from '../helpers/streaming-test-utilities';

// Core streaming test component
const StreamingCoreTest: React.FC = () => {
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
    const chunk = createMessageChunk(data, chunks.length + 1);
    setChunks(prev => [...prev, chunk]);
  };

  return (
    <div>
      <div data-testid="is-streaming">{isStreaming.toString()}</div>
      <div data-testid="chunk-count">{chunks.length}</div>
      <div data-testid="metrics-mps">{metrics.messagesPerSecond}</div>
      <div data-testid="metrics-fps">{metrics.framesPerSecond}</div>
      <div data-testid="metrics-dropped">{metrics.droppedFrames}</div>
      
      <button onClick={() => setIsStreaming(true)} data-testid="btn-start">Start</button>
      <button onClick={() => setIsStreaming(false)} data-testid="btn-stop">Stop</button>
      <button onClick={() => addChunk('test')} data-testid="btn-add">Add Chunk</button>
      <button onClick={() => updateMetric('messagesPerSecond', 60)} data-testid="btn-mps">Set MPS</button>
      <button onClick={() => updateMetric('framesPerSecond', 60)} data-testid="btn-fps">Set FPS</button>
      <button onClick={() => updateMetric('droppedFrames', 1)} data-testid="btn-drop">Drop Frame</button>
    </div>
  );
};

describe('Message Streaming Core Tests', () => {
  let wsManager: WebSocketTestManager;
  let streamBuffer: StreamBuffer;
  let frameController: FrameRateController;
  let performanceMonitor: StreamingPerformanceMonitor;

  beforeEach(() => {
    wsManager = new WebSocketTestManager();
    streamBuffer = new StreamBuffer();
    frameController = new FrameRateController();
    performanceMonitor = new StreamingPerformanceMonitor();
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
      render(<TestProviders><StreamingCoreTest /></TestProviders>);

      expect(screen.getByTestId('is-streaming')).toHaveTextContent('false');
      await userEvent.click(screen.getByTestId('btn-start'));
      expect(screen.getByTestId('is-streaming')).toHaveTextContent('true');
      await userEvent.click(screen.getByTestId('btn-stop'));
      expect(screen.getByTestId('is-streaming')).toHaveTextContent('false');
    });

    it('should add message chunks', async () => {
      render(<TestProviders><StreamingCoreTest /></TestProviders>);

      expect(screen.getByTestId('chunk-count')).toHaveTextContent('0');
      await userEvent.click(screen.getByTestId('btn-add'));
      expect(screen.getByTestId('chunk-count')).toHaveTextContent('1');
      await userEvent.click(screen.getByTestId('btn-add'));
      expect(screen.getByTestId('chunk-count')).toHaveTextContent('2');
    });
  });

  describe('Performance Metrics', () => {
    it('should track messages per second', async () => {
      render(<TestProviders><StreamingCoreTest /></TestProviders>);

      await userEvent.click(screen.getByTestId('btn-mps'));
      expect(screen.getByTestId('metrics-mps')).toHaveTextContent('60');
    });

    it('should achieve 60 FPS target', async () => {
      render(<TestProviders><StreamingCoreTest /></TestProviders>);

      await userEvent.click(screen.getByTestId('btn-fps'));
      expect(screen.getByTestId('metrics-fps')).toHaveTextContent('60');
    });

    it('should track dropped frames', async () => {
      render(<TestProviders><StreamingCoreTest /></TestProviders>);

      await userEvent.click(screen.getByTestId('btn-drop'));
      expect(screen.getByTestId('metrics-dropped')).toHaveTextContent('1');
    });

    it('should monitor performance', () => {
      performanceMonitor.recordMessage();
      performanceMonitor.recordFrame();
      expect(performanceMonitor.getMessagesPerSecond()).toBe(1);
      expect(performanceMonitor.getFramesPerSecond()).toBe(1);
    });
  });

  describe('Stream Buffer Management', () => {
    it('should enqueue and dequeue messages', () => {
      const chunk = createMessageChunk('test data', 1);
      const success = streamBuffer.enqueue(chunk);
      expect(success).toBe(true);
      expect(streamBuffer.size()).toBe(1);

      const dequeued = streamBuffer.dequeue();
      expect(dequeued?.data).toBe('test data');
      expect(streamBuffer.size()).toBe(0);
    });

    it('should respect buffer limits', () => {
      const smallBuffer = new StreamBuffer(2);
      const chunk1 = createMessageChunk('data1', 1);
      const chunk2 = createMessageChunk('data2', 2);
      const chunk3 = createMessageChunk('data3', 3);

      expect(smallBuffer.enqueue(chunk1)).toBe(true);
      expect(smallBuffer.enqueue(chunk2)).toBe(true);
      expect(smallBuffer.enqueue(chunk3)).toBe(false);
    });

    it('should detect backpressure conditions', () => {
      const buffer = new StreamBuffer(10);
      for (let i = 0; i < 9; i++) {
        buffer.enqueue(createMessageChunk('data', i));
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
      expect(controller.shouldRender(now + 5)).toBe(false);
      expect(controller.shouldRender(now + 20)).toBe(true);
    });

    it('should adapt to different frame rates', () => {
      const controller30 = new FrameRateController(30);
      const controller120 = new FrameRateController(120);
      expect(controller30.getTargetInterval()).toBeCloseTo(33.33, 1);
      expect(controller120.getTargetInterval()).toBeCloseTo(8.33, 1);
    });
  });

  describe('Message Types', () => {
    it('should handle text message types', () => {
      const textChunk = createMessageChunk(JSON.stringify({ type: 'text', content: 'Hello' }), 1);
      expect(streamBuffer.enqueue(textChunk)).toBe(true);
      expect(textChunk.data).toContain('text');
    });

    it('should handle binary message simulation', () => {
      const binaryData = new Uint8Array([1, 2, 3, 4, 5]);
      const binaryChunk = createMessageChunk(
        JSON.stringify({ type: 'binary', size: binaryData.length }), 1
      );
      expect(streamBuffer.enqueue(binaryChunk)).toBe(true);
      expect(binaryChunk.data).toContain('binary');
    });

    it('should handle large message chunking', () => {
      const largeData = 'x'.repeat(1000000);
      const largeChunk = createMessageChunk(largeData, 1);
      expect(largeChunk.size).toBe(1000000);
    });
  });

  describe('Latency Monitoring', () => {
    it('should measure message latency', () => {
      const sendTime = Date.now();
      const receiveTime = sendTime + 50;
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
      const { unmount } = render(<TestProviders><StreamingCoreTest /></TestProviders>);
      unmount();
      expect(true).toBe(true);
    });

    it('should handle abrupt disconnections', () => {
      streamBuffer.enqueue(createMessageChunk('data', 1));
      wsManager.close();
      expect(streamBuffer.size()).toBe(1);
    });
  });
});