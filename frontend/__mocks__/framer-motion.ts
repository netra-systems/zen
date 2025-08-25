/**
 * Mock implementation of framer-motion for testing
 * Replaces motion components with regular div elements
 */

import React from 'react';

// Mock motion components by replacing them with regular HTML elements
const mockMotionComponent = (Component: string) =>
  React.forwardRef<any, any>(({ children, ...props }, ref) => {
    // Remove framer-motion specific props to avoid React warnings
    const {
      initial,
      animate,
      exit,
      transition,
      variants,
      whileHover,
      whileTap,
      whileFocus,
      whileDrag,
      drag,
      dragConstraints,
      dragElastic,
      dragMomentum,
      onDragStart,
      onDragEnd,
      layout,
      layoutId,
      ...cleanProps
    } = props;

    return React.createElement(Component, {
      ref,
      'data-motion-component': Component,
      ...cleanProps
    }, children);
  });

// Create motion object with commonly used components
export const motion = {
  div: mockMotionComponent('div'),
  span: mockMotionComponent('span'),
  button: mockMotionComponent('button'),
  a: mockMotionComponent('a'),
  img: mockMotionComponent('img'),
  section: mockMotionComponent('section'),
  article: mockMotionComponent('article'),
  aside: mockMotionComponent('aside'),
  nav: mockMotionComponent('nav'),
  header: mockMotionComponent('header'),
  footer: mockMotionComponent('footer'),
  main: mockMotionComponent('main'),
  p: mockMotionComponent('p'),
  h1: mockMotionComponent('h1'),
  h2: mockMotionComponent('h2'),
  h3: mockMotionComponent('h3'),
  h4: mockMotionComponent('h4'),
  h5: mockMotionComponent('h5'),
  h6: mockMotionComponent('h6'),
  ul: mockMotionComponent('ul'),
  ol: mockMotionComponent('ol'),
  li: mockMotionComponent('li'),
  form: mockMotionComponent('form'),
  input: mockMotionComponent('input'),
  textarea: mockMotionComponent('textarea'),
  select: mockMotionComponent('select'),
  option: mockMotionComponent('option'),
  label: mockMotionComponent('label'),
  table: mockMotionComponent('table'),
  thead: mockMotionComponent('thead'),
  tbody: mockMotionComponent('tbody'),
  tfoot: mockMotionComponent('tfoot'),
  tr: mockMotionComponent('tr'),
  th: mockMotionComponent('th'),
  td: mockMotionComponent('td'),
  canvas: mockMotionComponent('canvas'),
  svg: mockMotionComponent('svg'),
  path: mockMotionComponent('path'),
  circle: mockMotionComponent('circle'),
  rect: mockMotionComponent('rect'),
  line: mockMotionComponent('line'),
  polyline: mockMotionComponent('polyline'),
  polygon: mockMotionComponent('polygon')
};

// Mock other framer-motion exports
export const AnimatePresence: React.FC<{ children: React.ReactNode; mode?: string }> = ({ children }) => 
  React.createElement(React.Fragment, null, children);

export const useAnimation = () => ({
  start: jest.fn(),
  stop: jest.fn(),
  set: jest.fn(),
});

export const useMotionValue = (initialValue: any) => ({
  get: () => initialValue,
  set: jest.fn(),
  onChange: jest.fn(),
});

export const useTransform = () => initialValue => initialValue;

export const useSpring = () => ({
  get: () => 0,
  set: jest.fn(),
});

export const useDragControls = () => ({
  start: jest.fn(),
});

export const useMotionTemplate = () => '';

export const useInView = () => [React.useRef(), false];

export const useScroll = () => ({
  scrollX: { get: () => 0 },
  scrollY: { get: () => 0 },
  scrollXProgress: { get: () => 0 },
  scrollYProgress: { get: () => 0 },
});

// Export default motion object
export default motion;