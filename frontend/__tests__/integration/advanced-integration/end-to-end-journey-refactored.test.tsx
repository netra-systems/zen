import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { setupTestEnvironment, cleanupTestEnvironment } from '../../helpers/test-setup-helpers';
import { createOptimizationWorkflowComponent, createTestFile, simulateFileInput } from '../../helpers/optimization-workflow-helpers';
import { assertElementText, waitForElementText, assertOptimizationResults } from '../../helpers/test-assertion-helpers';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
{ assertElementText, waitForElementText, assertOptimizationResults } from '../../helpers/test-assertion-helpers';

describe('Advanced Frontend Integration Tests - End-to-End Journey', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    setupTestEnvironment();
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('30. End-to-End User Journey', () => {
      jest.setTimeout(10000);
    it('should complete full optimization workflow', async () => {
      const OptimizationWorkflow = createOptimizationWorkflowComponent();
      const { getByTestId, getByText } = render(<OptimizationWorkflow />);
      
      await executeUploadStep(getByTestId);
      await executeAnalysisStep(getByText);
      await executeReviewStep(getByTestId, getByText);
      await verifyCompletionStep(getByTestId);
    });
  });
});

const executeUploadStep = async (getByTestId: any) => {
  assertElementText('current-step', 'upload');
  const file = createTestFile();
  const input = getByTestId('file-input') as HTMLInputElement;
  simulateFileInput(input, file);
  fireEvent.change(input);
  await waitForElementText('current-step', 'analyze');
};

const executeAnalysisStep = async (getByText: any) => {
  fireEvent.click(getByText('Start Analysis'));
  await waitForElementText('current-step', 'review');
};

const executeReviewStep = async (getByTestId: any, getByText: any) => {
  assertElementText('optimization-count', '2 optimizations found');
  fireEvent.click(getByText('Apply All'));
  await waitForElementText('current-step', 'complete');
};

const verifyCompletionStep = async (getByTestId: any) => {
  assertOptimizationResults('results', '45%', '30ms');
};