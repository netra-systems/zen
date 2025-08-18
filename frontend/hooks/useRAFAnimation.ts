/**
 * React Hook for RAF-based Animations with Spring Physics
 * Provides smooth 60fps animations with automatic cleanup
 */

import { useRef, useCallback, useEffect } from 'react';
import { animationEngine, type AnimationConfig } from '../services/animation-engine';

interface SpringConfig {
  tension?: number;
  friction?: number;
  mass?: number;
}

interface AnimationOptions extends AnimationConfig {
  spring?: SpringConfig;
  autoStart?: boolean;
}

interface AnimationControls {
  start: (values: Record<string, number>) => void;
  stop: () => void;
  isAnimating: boolean;
}

export function useRAFAnimation(options: AnimationOptions = {}): [React.RefObject<HTMLElement>, AnimationControls] {
  const elementRef = useRef<HTMLElement>(null);
  const animationIdRef = useRef<string>('');
  const isAnimatingRef = useRef<boolean>(false);

  const generateId = useCallback((): string => {
    return `anim_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  const start = useCallback((values: Record<string, number>) => {
    if (!elementRef.current) return;
    const id = generateId();
    animationIdRef.current = id;
    isAnimatingRef.current = true;
    animationEngine.animate(id, elementRef.current, values, {
      ...options,
      callback: () => { isAnimatingRef.current = false; }
    });
  }, [options, generateId]);

  const stop = useCallback(() => {
    if (animationIdRef.current) {
      animationEngine.cancelAnimation(animationIdRef.current);
      isAnimatingRef.current = false;
    }
  }, []);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  const controls: AnimationControls = {
    start,
    stop,
    isAnimating: isAnimatingRef.current
  };

  return [elementRef, controls];
}

export function useSpringAnimation(config: SpringConfig = {}): [React.RefObject<HTMLElement>, AnimationControls] {
  const { tension = 170, friction = 26, mass = 1 } = config;
  
  const springOptions: AnimationOptions = {
    duration: calculateSpringDuration(tension, friction, mass),
    easing: 'ease-out'
  };

  return useRAFAnimation(springOptions);
}

function calculateSpringDuration(tension: number, friction: number, mass: number): number {
  const dampingRatio = friction / (2 * Math.sqrt(tension * mass));
  const undampedFreq = Math.sqrt(tension / mass);
  const dampedFreq = undampedFreq * Math.sqrt(1 - dampingRatio * dampingRatio);
  return Math.max(300, (Math.PI * 2) / dampedFreq * 1000 * 0.8);
}

export function useSequentialAnimation(): [(values: Record<string, number>[]) => void, () => void] {
  const animationsRef = useRef<Array<() => void>>([]);

  const startSequence = useCallback((valueSequence: Record<string, number>[]) => {
    valueSequence.forEach((values, index) => {
      setTimeout(() => {
        animationsRef.current[index]?.();
      }, index * 100);
    });
  }, []);

  const stopSequence = useCallback(() => {
    animationsRef.current.forEach(stop => stop());
  }, []);

  return [startSequence, stopSequence];
}