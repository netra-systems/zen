/**
 * Streaming Test Utilities
 * Utilities for streaming and backpressure testing
 * Agent 10 Implementation - Streaming performance helpers
 */

import { MessageChunk } from './websocket-test-utilities';

// Frame rate controller
export class FrameRateController {
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

  getTargetInterval(): number { return this.frameInterval; }
}

// Streaming performance monitor
export class StreamingPerformanceMonitor {
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

  recordDroppedFrame(): void { this.droppedFrames++; }
  getMessagesPerSecond(): number { return this.messageTimestamps.length; }
  getFramesPerSecond(): number { return this.frameTimestamps.length; }
  getDroppedFrames(): number { return this.droppedFrames; }

  private cleanOldTimestamps(): void {
    const oneSecondAgo = Date.now() - 1000;
    this.messageTimestamps = this.messageTimestamps.filter(t => t > oneSecondAgo);
    this.frameTimestamps = this.frameTimestamps.filter(t => t > oneSecondAgo);
  }
}

// Backpressure handler
export class BackpressureHandler {
  private threshold: number;
  private events: number = 0;

  constructor(threshold: number = 100) { this.threshold = threshold; }
  getEventCount(): number { return this.events; }
  reset(): void { this.events = 0; }

  checkBackpressure(bufferSize: number): boolean {
    if (bufferSize > this.threshold) {
      this.events++;
      return true;
    }
    return false;
  }
}

// Stream buffer with backpressure
export class StreamBuffer {
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