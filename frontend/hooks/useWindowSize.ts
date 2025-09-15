import { useState, useEffect } from 'react';

interface WindowSize {
  width: number;
  height: number;
}

export const useWindowSize = (): WindowSize => {
  const [windowSize, setWindowSize] = useState<WindowSize>({
    width: 0,
    height: 0,
  });

  useEffect(() => {
    // Handler to call on window resize
    function handleResize() {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    }

    // Add event listener
    window.addEventListener('resize', handleResize);

    // Call handler right away so state gets updated with initial window size
    handleResize();

    // Remove event listener on cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []); // Empty array ensures that effect is only run on mount

  return windowSize;
};

/**
 * Hook for responsive height management with constraints
 * Calculates Math.min(windowHeight * 0.8, 800) for optimal container height
 */
export const useResponsiveHeight = () => {
  const { height } = useWindowSize();
  
  // Calculate responsive height with max constraint
  const responsiveHeight = Math.min(height * 0.8, 800);
  
  // Calculate different height variants for different components
  const heights = {
    // Main responsive height (80% of window, max 800px)
    primary: responsiveHeight,
    
    // Secondary height for smaller panels (60% of window, max 600px)
    secondary: Math.min(height * 0.6, 600),
    
    // Compact height for minimal panels (40% of window, max 400px)
    compact: Math.min(height * 0.4, 400),
    
    // CSS custom properties for inline styles
    css: {
      '--responsive-height-primary': `${responsiveHeight}px`,
      '--responsive-height-secondary': `${Math.min(height * 0.6, 600)}px`,
      '--responsive-height-compact': `${Math.min(height * 0.4, 400)}px`,
    } as React.CSSProperties,
    
    // Tailwind-compatible height classes
    tailwind: {
      primary: `h-[${responsiveHeight}px]`,
      secondary: `h-[${Math.min(height * 0.6, 600)}px]`,
      compact: `h-[${Math.min(height * 0.4, 400)}px]`,
    }
  };
  
  return {
    windowHeight: height,
    ...heights
  };
};

/**
 * Hook for determining if height constraints should be applied
 * Useful for conditional styling based on window size
 */
export const useHeightConstraints = () => {
  const { height } = useWindowSize();
  
  const isVeryTallScreen = height > 1000;  // > 1000px height
  const isTallScreen = height > 800;       // > 800px height
  const isShortScreen = height < 600;      // < 600px height
  const isVeryShortScreen = height < 400;  // < 400px height
  
  return {
    windowHeight: height,
    isVeryTallScreen,
    isTallScreen,
    isShortScreen,
    isVeryShortScreen,
    shouldUseConstraints: isTallScreen, // Apply height constraints for tall screens
    heightClass: isVeryShortScreen ? 'h-full' : 
                 isShortScreen ? 'max-h-[90vh]' : 
                 isTallScreen ? 'max-h-[80vh]' : 'max-h-[800px]'
  };
};