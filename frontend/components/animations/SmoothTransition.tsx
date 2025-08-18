/**
 * SmoothTransition - GPU-Accelerated Transition Wrapper
 * Provides smooth transitions with configurable easing and duration
 */

import React, { useEffect, useRef } from 'react';
import { useRAFAnimation } from '../../hooks/useRAFAnimation';

interface SmoothTransitionProps {
  children: React.ReactNode;
  isVisible?: boolean;
  duration?: number;
  easing?: 'ease-in' | 'ease-out' | 'ease-in-out' | 'linear';
  direction?: 'up' | 'down' | 'left' | 'right' | 'fade' | 'scale';
  className?: string;
  onComplete?: () => void;
}

interface TransitionConfig {
  initial: Record<string, number>;
  animate: Record<string, number>;
}

export function SmoothTransition({
  children,
  isVisible = true,
  duration = 300,
  easing = 'ease-out',
  direction = 'fade',
  className = '',
  onComplete
}: SmoothTransitionProps): JSX.Element {
  const [elementRef, controls] = useRAFAnimation({
    duration,
    easing,
    callback: onComplete
  });
  const previousVisible = useRef<boolean>(isVisible);

  const getTransitionConfig = (): TransitionConfig => {
    switch (direction) {
      case 'up': return {
        initial: { translateY: 20, opacity: 0 },
        animate: { translateY: 0, opacity: 1 }
      };
      case 'down': return {
        initial: { translateY: -20, opacity: 0 },
        animate: { translateY: 0, opacity: 1 }
      };
      case 'left': return {
        initial: { translateX: 20, opacity: 0 },
        animate: { translateX: 0, opacity: 1 }
      };
      case 'right': return {
        initial: { translateX: -20, opacity: 0 },
        animate: { translateX: 0, opacity: 1 }
      };
      case 'scale': return {
        initial: { scale: 0.95, opacity: 0 },
        animate: { scale: 1, opacity: 1 }
      };
      default: return {
        initial: { opacity: 0 },
        animate: { opacity: 1 }
      };
    }
  };

  const setInitialState = (): void => {
    if (!elementRef.current) return;
    const config = getTransitionConfig();
    const element = elementRef.current;
    Object.entries(config.initial).forEach(([prop, value]) => {
      if (prop.includes('translate') || prop.includes('scale')) {
        element.style.transform = `${prop}(${value}${getUnit(prop)})`;
      } else {
        element.style.setProperty(prop, value.toString());
      }
    });
  };

  const getUnit = (property: string): string => {
    if (property.includes('scale')) return '';
    if (property.includes('translate')) return 'px';
    return '';
  };

  useEffect(() => {
    if (isVisible !== previousVisible.current) {
      previousVisible.current = isVisible;
      const config = getTransitionConfig();
      const targetValues = isVisible ? config.animate : config.initial;
      controls.start(targetValues);
    }
  }, [isVisible, controls]);

  useEffect(() => {
    setInitialState();
    if (isVisible) {
      const config = getTransitionConfig();
      controls.start(config.animate);
    }
  }, []);

  return (
    <div 
      ref={elementRef}
      className={`transform-gpu ${className}`}
      style={{
        willChange: 'transform, opacity',
        transform: 'translateZ(0)'
      }}
    >
      {children}
    </div>
  );
}