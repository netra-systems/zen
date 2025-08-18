/**
 * High-Performance Animation Engine with RAF Scheduling
 * Provides 60fps animations with GPU acceleration and batch DOM updates
 */

interface AnimationConfig {
  duration?: number;
  easing?: string;
  transform?: boolean;
  callback?: () => void;
}

interface AnimationFrame {
  id: string;
  element: HTMLElement;
  startTime: number;
  config: AnimationConfig;
  startValues: Record<string, number>;
  endValues: Record<string, number>;
}

interface PerformanceMetrics {
  frameCount: number;
  droppedFrames: number;
  lastFPS: number;
  avgFrameTime: number;
}

class AnimationEngine {
  private static instance: AnimationEngine;
  private rafId: number | null = null;
  private animations = new Map<string, AnimationFrame>();
  private batchUpdates: Array<() => void> = [];
  private metrics: PerformanceMetrics = {
    frameCount: 0,
    droppedFrames: 0,
    lastFPS: 60,
    avgFrameTime: 16.67
  };

  static getInstance(): AnimationEngine {
    if (!AnimationEngine.instance) {
      AnimationEngine.instance = new AnimationEngine();
    }
    return AnimationEngine.instance;
  }

  private constructor() {
    this.startRAFLoop();
  }

  private startRAFLoop(): void {
    const tick = (timestamp: number) => {
      this.processFrame(timestamp);
      this.rafId = requestAnimationFrame(tick);
    };
    this.rafId = requestAnimationFrame(tick);
  }

  private processFrame(timestamp: number): void {
    this.updateMetrics(timestamp);
    this.processBatchUpdates();
    this.updateAnimations(timestamp);
    this.cleanupCompletedAnimations();
  }

  private updateMetrics(timestamp: number): void {
    this.metrics.frameCount++;
    const frameTime = timestamp - (this.lastFrameTime || timestamp);
    this.metrics.avgFrameTime = frameTime;
    this.metrics.lastFPS = 1000 / frameTime;
    this.lastFrameTime = timestamp;
  }

  private processBatchUpdates(): void {
    const updates = [...this.batchUpdates];
    this.batchUpdates.length = 0;
    updates.forEach(update => update());
  }

  private updateAnimations(timestamp: number): void {
    this.animations.forEach((animation, id) => {
      const progress = this.calculateProgress(animation, timestamp);
      this.applyAnimation(animation, progress);
    });
  }

  private calculateProgress(animation: AnimationFrame, timestamp: number): number {
    const elapsed = timestamp - animation.startTime;
    const duration = animation.config.duration || 300;
    const progress = Math.min(elapsed / duration, 1);
    return this.applyEasing(progress, animation.config.easing);
  }

  private applyEasing(progress: number, easing?: string): number {
    switch (easing) {
      case 'ease-out': return 1 - Math.pow(1 - progress, 3);
      case 'ease-in': return Math.pow(progress, 3);
      case 'ease-in-out': return progress < 0.5 ? 
        4 * Math.pow(progress, 3) : 
        1 - Math.pow(-2 * progress + 2, 3) / 2;
      default: return progress;
    }
  }

  private applyAnimation(animation: AnimationFrame, progress: number): void {
    const { element, startValues, endValues, config } = animation;
    const transforms: string[] = [];
    Object.keys(endValues).forEach(prop => {
      const start = startValues[prop] || 0;
      const end = endValues[prop];
      const current = start + (end - start) * progress;
      this.setProperty(element, prop, current, transforms);
    });
  }

  private setProperty(element: HTMLElement, prop: string, value: number, transforms: string[]): void {
    if (prop.includes('translate') || prop.includes('scale') || prop.includes('rotate')) {
      transforms.push(`${prop}(${value}${this.getUnit(prop)})`);
      element.style.transform = transforms.join(' ');
    } else {
      element.style.setProperty(prop, `${value}${this.getUnit(prop)}`);
    }
  }

  private getUnit(property: string): string {
    if (property.includes('rotate')) return 'deg';
    if (property.includes('scale')) return '';
    if (property.includes('translate') || property.includes('opacity')) return property.includes('opacity') ? '' : 'px';
    return 'px';
  }

  private cleanupCompletedAnimations(): void {
    this.animations.forEach((animation, id) => {
      const elapsed = performance.now() - animation.startTime;
      const duration = animation.config.duration || 300;
      if (elapsed >= duration) {
        animation.config.callback?.();
        this.animations.delete(id);
      }
    });
  }

  public animate(id: string, element: HTMLElement, endValues: Record<string, number>, config: AnimationConfig = {}): void {
    const startValues = this.getCurrentValues(element, Object.keys(endValues));
    const animation: AnimationFrame = {
      id,
      element,
      startTime: performance.now(),
      config,
      startValues,
      endValues
    };
    this.animations.set(id, animation);
  }

  private getCurrentValues(element: HTMLElement, properties: string[]): Record<string, number> {
    const values: Record<string, number> = {};
    properties.forEach(prop => {
      values[prop] = this.parseValue(getComputedStyle(element).getPropertyValue(prop));
    });
    return values;
  }

  private parseValue(value: string): number {
    return parseFloat(value) || 0;
  }

  public batchUpdate(updateFn: () => void): void {
    this.batchUpdates.push(updateFn);
  }

  public cancelAnimation(id: string): void {
    this.animations.delete(id);
  }

  public getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  public destroy(): void {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.animations.clear();
    this.batchUpdates.length = 0;
  }

  private lastFrameTime?: number;
}

export const animationEngine = AnimationEngine.getInstance();
export type { AnimationConfig, PerformanceMetrics };