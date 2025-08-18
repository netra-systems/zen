/**
 * Animation Helpers - Easing Functions & Transform Utilities
 * Provides comprehensive animation utilities for smooth 60fps performance
 */

// Cubic Bezier Easing Functions
export const easingFunctions = {
  linear: (t: number): number => t,
  easeInQuad: (t: number): number => t * t,
  easeOutQuad: (t: number): number => t * (2 - t),
  easeInOutQuad: (t: number): number => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,
  easeInCubic: (t: number): number => t * t * t,
  easeOutCubic: (t: number): number => (--t) * t * t + 1,
  easeInOutCubic: (t: number): number => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  easeInQuart: (t: number): number => t * t * t * t
};

// Spring Physics Configuration
interface SpringParams {
  tension: number;
  friction: number;
  mass: number;
}

export function createSpringEasing(params: SpringParams): (t: number) => number {
  const { tension = 170, friction = 26, mass = 1 } = params;
  return (t: number): number => {
    const dampingRatio = friction / (2 * Math.sqrt(tension * mass));
    const undampedFreq = Math.sqrt(tension / mass);
    
    if (dampingRatio < 1) {
      const dampedFreq = undampedFreq * Math.sqrt(1 - dampingRatio * dampingRatio);
      return 1 - Math.exp(-dampingRatio * undampedFreq * t) * 
        Math.cos(dampedFreq * t);
    }
    return 1 - Math.exp(-undampedFreq * t) * (1 + undampedFreq * t);
  };
}

// Bounce Easing Implementation
export function bounceEasing(t: number): number {
  if (t < 1 / 2.75) {
    return 7.5625 * t * t;
  } else if (t < 2 / 2.75) {
    return 7.5625 * (t -= 1.5 / 2.75) * t + 0.75;
  } else if (t < 2.5 / 2.75) {
    return 7.5625 * (t -= 2.25 / 2.75) * t + 0.9375;
  }
  return 7.5625 * (t -= 2.625 / 2.75) * t + 0.984375;
}

// Transform Utilities for GPU Acceleration
export interface Transform3D {
  translateX?: number;
  translateY?: number;
  translateZ?: number;
  rotateX?: number;
  rotateY?: number;
  rotateZ?: number;
  scaleX?: number;
  scaleY?: number;
  scaleZ?: number;
}

export function buildTransform3D(transform: Transform3D): string {
  const parts: string[] = [];
  
  if (transform.translateX !== undefined) parts.push(`translateX(${transform.translateX}px)`);
  if (transform.translateY !== undefined) parts.push(`translateY(${transform.translateY}px)`);
  if (transform.translateZ !== undefined) parts.push(`translateZ(${transform.translateZ}px)`);
  if (transform.rotateX !== undefined) parts.push(`rotateX(${transform.rotateX}deg)`);
  if (transform.rotateY !== undefined) parts.push(`rotateY(${transform.rotateY}deg)`);
  if (transform.rotateZ !== undefined) parts.push(`rotateZ(${transform.rotateZ}deg)`);
  if (transform.scaleX !== undefined) parts.push(`scaleX(${transform.scaleX})`);
  if (transform.scaleY !== undefined) parts.push(`scaleY(${transform.scaleY})`);
  
  return parts.join(' ');
}

// Performance Monitoring
export class PerformanceMonitor {
  private frameCount = 0;
  private lastTime = performance.now();
  private fps = 60;

  measureFrame(): number {
    this.frameCount++;
    const currentTime = performance.now();
    const delta = currentTime - this.lastTime;
    
    if (delta >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / delta);
      this.frameCount = 0;
      this.lastTime = currentTime;
    }
    
    return this.fps;
  }

  getFPS(): number {
    return this.fps;
  }
}

// Batch Update Manager
export class BatchUpdateManager {
  private updates: Array<() => void> = [];
  private rafId: number | null = null;

  add(updateFn: () => void): void {
    this.updates.push(updateFn);
    this.scheduleFlush();
  }

  private scheduleFlush(): void {
    if (this.rafId) return;
    this.rafId = requestAnimationFrame(() => {
      this.flush();
    });
  }

  private flush(): void {
    const updates = [...this.updates];
    this.updates.length = 0;
    this.rafId = null;
    updates.forEach(update => update());
  }
}

// Animation Utility Functions
export function interpolate(start: number, end: number, progress: number): number {
  return start + (end - start) * progress;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function mapRange(value: number, inMin: number, inMax: number, outMin: number, outMax: number): number {
  return (value - inMin) * (outMax - outMin) / (inMax - inMin) + outMin;
}

export function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

// GPU-Optimized Style Application
export function applyGPUStyles(element: HTMLElement): void {
  element.style.willChange = 'transform, opacity';
  element.style.transform = 'translateZ(0)';
  element.style.backfaceVisibility = 'hidden';
  element.style.perspective = '1000px';
}

export function removeGPUStyles(element: HTMLElement): void {
  element.style.willChange = 'auto';
  element.style.transform = '';
  element.style.backfaceVisibility = '';
  element.style.perspective = '';
}

// Animation Timing Functions
export function getAnimationDuration(distance: number, velocity = 1): number {
  return Math.max(200, Math.min(800, distance / velocity));
}

export function calculateOptimalFrames(duration: number, targetFPS = 60): number {
  return Math.ceil((duration / 1000) * targetFPS);
}