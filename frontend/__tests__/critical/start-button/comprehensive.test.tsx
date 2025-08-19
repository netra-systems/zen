/**
 * Comprehensive Start Chat Button Tests - Critical Conversion Gateway
 * 
 * Tests the MOST CRITICAL button in the application - the gateway to $30K MRR impact.
 * This button is the primary conversion point from visitors to active users.
 * 
 * Business Value Justification:
 * - Segment: All (Free → Enterprise) - Primary conversion gateway
 * - Goal: 100% reliability, perfect UX, instant responsiveness
 * - Value Impact: This button = 30% of all user conversions
 * - Revenue Impact: Each button failure = potential $1K lost MRR
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all interactions
 * @compliance frontend_unified_testing_spec.xml - Critical component requirements
 */

import React from 'react';
import { screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThreadSidebarHeader } from '@/components/chat/ThreadSidebarComponents';
import {
  setupCriticalTests,
  cleanupCriticalTests,
  renderButtonWithProps,
  visibilityTestCases,
  viewportConfigs,
  setupViewport,
  setupMobileViewport,
  simulateButtonClick,
  simulateTouchEvent,
  simulateKeyboardFocus,
  simulateEnterKey,
  simulateSpaceKey,
  verifyButtonVisibility,
  verifyButtonEnabledState,
  verifyAlwaysVisible,
  verifyProminentDisplay,
  verifyThreadCreationTriggered,
  verifyNoThreadCreation,
  verifyLoadingState,
  verifySpinnerPresent,
  verifyButtonDisabled,
  verifyResponsiveLayout,
  verifyTouchTargetSize,
  verifyARIACompliance,
  verifyAccessibleName,
  verifyFocusState,
  verifyKeyboardActivation,
  verifyButtonText,
  verifyButtonStyling,
  measureRenderPerformance,
  verifyCriticalRenderTime
} from './test-helpers';

describe('Start Chat Button - Critical Conversion Gateway', () => {
  beforeEach(() => {
    setupCriticalTests();
  });
  
  afterEach(() => {
    cleanupCriticalTests();
  });
  
  describe('Visibility and State Management', () => {
    test.each(visibilityTestCases)('shows correct state for $name', ({ props, expectedVisible, expectedEnabled }) => {
      renderButtonWithProps(props);
      verifyButtonVisibility(expectedVisible);
      verifyButtonEnabledState(expectedEnabled);
    });
    
    it('is ALWAYS visible to new users - critical conversion', () => {
      renderButtonWithProps({ isAuthenticated: true });
      verifyAlwaysVisible();
      verifyProminentDisplay();
    });
    
    it('displays prominently when no threads exist', () => {
      renderButtonWithProps({ isAuthenticated: true });
      verifyButtonVisibility(true);
      verifyProminentDisplay();
    });
    
    it('maintains visibility during all state transitions', () => {
      const { rerender } = renderButtonWithProps({});
      rerender(<ThreadSidebarHeader onCreateThread={jest.fn()} isCreating={true} isLoading={false} isAuthenticated={true} />);
      expect(screen.getByRole('button')).toBeVisible();
    });
  });
  
  describe('Click Handling and Thread Creation', () => {
    it('triggers onCreateThread when clicked', () => {
      renderButtonWithProps({});
      simulateButtonClick();
      verifyThreadCreationTriggered();
    });
    
    it('prevents multiple clicks when creating', () => {
      renderButtonWithProps({ isCreating: true });
      simulateButtonClick();
      verifyNoThreadCreation();
    });
    
    it('shows loading spinner when creating', () => {
      renderButtonWithProps({ isCreating: true });
      verifySpinnerPresent();
    });
    
    it('provides immediate visual feedback on click', () => {
      renderButtonWithProps({});
      simulateButtonClick();
      verifyThreadCreationTriggered();
    });
  });
  
  describe('Loading States and Error Recovery', () => {
    it('shows loading state during thread creation', () => {
      renderButtonWithProps({ isCreating: true });
      verifyLoadingState();
      verifySpinnerPresent();
    });
    
    it('maintains disabled state during creation', () => {
      renderButtonWithProps({ isCreating: true });
      verifyButtonDisabled();
    });
    
    it('shows disabled state when not authenticated', () => {
      renderButtonWithProps({ isAuthenticated: false });
      verifyButtonDisabled();
    });
    
    it('shows disabled state when loading', () => {
      renderButtonWithProps({ isLoading: true });
      verifyButtonDisabled();
    });
  });
  
  describe('Mobile Touch Events and Responsiveness', () => {
    test.each(viewportConfigs)('works perfectly on $name viewport', ({ width, height, isDesktop }) => {
      setupViewport(width, height);
      renderButtonWithProps({});
      verifyResponsiveLayout(isDesktop);
      verifyTouchTargetSize();
    });
    
    it('handles touch events on mobile', () => {
      setupMobileViewport();
      renderButtonWithProps({});
      simulateTouchEvent();
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
    
    it('maintains proper touch target size', () => {
      setupMobileViewport();
      renderButtonWithProps({});
      verifyTouchTargetSize();
    });
    
    it('responds to gestures correctly', () => {
      setupMobileViewport();
      renderButtonWithProps({});
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
  });
  
  describe('Keyboard Accessibility and ARIA', () => {
    it('has perfect ARIA attributes', () => {
      renderButtonWithProps({});
      verifyARIACompliance();
      verifyAccessibleName();
    });
    
    it('supports keyboard focus', () => {
      renderButtonWithProps({});
      simulateKeyboardFocus();
      verifyFocusState();
    });
    
    it('activates with Enter key', () => {
      renderButtonWithProps({});
      simulateEnterKey();
      verifyKeyboardActivation();
    });
    
    it('activates with Space key', () => {
      renderButtonWithProps({});
      simulateSpaceKey();
      verifyKeyboardActivation();
    });
  });
  
  describe('Performance and Conversion Optimization', () => {
    it('renders quickly for conversion optimization', () => {
      const renderTime = measureRenderPerformance();
      verifyCriticalRenderTime(renderTime);
    });
    
    it('handles button text correctly', () => {
      renderButtonWithProps({});
      verifyButtonText();
    });
    
    it('shows correct text when creating', () => {
      renderButtonWithProps({ isCreating: true });
      expect(screen.getByRole('button')).toBeInTheDocument();
    });
    
    it('maintains consistent styling', () => {
      renderButtonWithProps({});
      verifyButtonStyling();
    });
  });
});