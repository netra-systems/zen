import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { teractive Features Animation Integration Tests
 * ULTRA DEEP THINK: Module-based architecture - Animation tests extracted for 450-line compliance
 */

import {
  React, render, waitFor, fireEvent, TEST_TIMEOUTS,
  setupInteractiveTest, teardownInteractiveTest,
  waitForUserInteraction, getMovementDirection, calculateNewPosition,
  expectAnimationStage, expectAnimationStatus, expectGesturePosition
} from './interactive-features-utils';

describe('Complex Animation Sequences Tests', () => {
    jest.setTimeout(10000);
  let server: any;
  
  beforeEach(() => {
    server = setupInteractiveTest();
  });

  afterEach(() => {
    teardownInteractiveTest();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });
  it('should chain animations with proper timing', async () => {
    const AnimationComponent = () => {
      const [stage, setStage] = React.useState(0);
      const [isAnimating, setIsAnimating] = React.useState(false);
      
      const executeAnimationStage = async (stageNumber: number) => {
        setStage(stageNumber);
        await waitForUserInteraction(100);
      };
      
      const runAnimation = async () => {
        setIsAnimating(true);
        await executeAnimationStage(1);
        await executeAnimationStage(2);
        await executeAnimationStage(3);
        setIsAnimating(false);
      };
      
      const resetAnimation = () => {
        setStage(0);
        setIsAnimating(false);
      };
      
      return (
        <div>
          <button onClick={runAnimation} disabled={isAnimating}>
            Start Animation
          </button>
          <button onClick={resetAnimation}>Reset</button>
          <div
            data-testid="animated-element"
            style={{
              transform: `translateX(${stage * 50}px) scale(${1 + stage * 0.1})`,
              transition: 'all 0.1s ease-in-out',
              opacity: stage > 0 ? 1 : 0.5
            }}
          >
            Stage {stage}
          </div>
          <div data-testid="animation-status">
            {isAnimating ? 'Animating' : 'Idle'}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(<AnimationComponent />);
    
    expectAnimationStage(getByTestId, 0);
    expectAnimationStatus(getByTestId, 'Idle');
    
    fireEvent.click(getByText('Start Animation'));
    
    await waitFor(() => {
      expectAnimationStatus(getByTestId, 'Animating');
      expectAnimationStage(getByTestId, 1);
    });
    
    await waitFor(() => {
      expectAnimationStage(getByTestId, 2);
    }, { timeout: 200 });
    
    await waitFor(() => {
      expectAnimationStage(getByTestId, 3);
    }, { timeout: 300 });
    
    await waitFor(() => {
      expectAnimationStatus(getByTestId, 'Idle');
    }, { timeout: 400 });
  });

  it('should handle gesture-based animations', async () => {
    const GestureComponent = () => {
      const [position, setPosition] = React.useState({ x: 0, y: 0 });
      const [isMoving, setIsMoving] = React.useState(false);
      const [history, setHistory] = React.useState<Array<{ x: number, y: number }>>([]);
      
      const updatePositionAndHistory = (newPosition: { x: number, y: number }) => {
        setPosition(newPosition);
        setHistory(prev => [...prev, newPosition]);
      };
      
      const handleSwipe = async (direction: string, distance: number = 100) => {
        setIsMoving(true);
        const movement = getMovementDirection(direction, distance);
        const newPosition = calculateNewPosition(position, movement);
        updatePositionAndHistory(newPosition);
        await waitForUserInteraction(200);
        setIsMoving(false);
      };
      
      const resetPosition = () => {
        setPosition({ x: 0, y: 0 });
        setHistory([]);
      };
      
      return (
        <div>
          <div style={{ margin: '10px 0' }}>
            <button onClick={() => handleSwipe('right')}>Swipe Right</button>
            <button onClick={() => handleSwipe('left')}>Swipe Left</button>
            <button onClick={() => handleSwipe('up')}>Swipe Up</button>
            <button onClick={() => handleSwipe('down')}>Swipe Down</button>
            <button onClick={resetPosition}>Reset</button>
          </div>
          <div
            data-testid="gesture-element"
            style={{
              transform: `translate(${position.x}px, ${position.y}px)`,
              transition: 'transform 0.2s ease-out',
              display: 'inline-block',
              padding: '10px',
              border: '2px solid',
              borderColor: isMoving ? 'red' : 'blue'
            }}
          >
            Position: {position.x}, {position.y}
          </div>
          <div data-testid="move-count">{history.length} moves</div>
          <div data-testid="moving-status">
            {isMoving ? 'Moving' : 'Stopped'}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(<GestureComponent />);
    
    expectGesturePosition(getByTestId, 0, 0);
    expect(getByTestId('move-count')).toHaveTextContent('0 moves');
    
    fireEvent.click(getByText('Swipe Right'));
    
    await waitFor(() => {
      expect(getByTestId('moving-status')).toHaveTextContent('Moving');
    });
    
    await waitFor(() => {
      expectGesturePosition(getByTestId, 100, 0);
      expect(getByTestId('move-count')).toHaveTextContent('1 moves');
      expect(getByTestId('moving-status')).toHaveTextContent('Stopped');
    }, { timeout: TEST_TIMEOUTS.SHORT });
    
    fireEvent.click(getByText('Swipe Left'));
    
    await waitFor(() => {
      expectGesturePosition(getByTestId, 0, 0);
      expect(getByTestId('move-count')).toHaveTextContent('2 moves');
    }, { timeout: TEST_TIMEOUTS.SHORT });
  });
});