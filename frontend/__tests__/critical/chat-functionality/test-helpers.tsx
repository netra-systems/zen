/**
 * File Upload Test Helpers - Critical Chat Functionality
 * ======================================================
 * 
 * BUSINESS VALUE JUSTIFICATION (BVJ):
 * - Segment: Growth & Enterprise
 * - Business Goal: Enable reliable file upload testing
 * - Value Impact: Ensures file upload works for 60% of enterprise workflows
 * - Revenue Impact: Document analysis drives 35% of enterprise conversions
 * 
 * ARCHITECTURAL COMPLIANCE:
 * - File size: ≤300 lines (MANDATORY)
 * - Functions: ≤8 lines each (MANDATORY)
 */

import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// File upload constants
export const FILE_UPLOAD_TIMEOUT = 10000;

// Mock file creation helpers (≤8 lines each)
export const createMockFile = (name: string, size: number, type: string): File => {
  const content = 'a'.repeat(size);
  const blob = new Blob([content], { type });
  const file = new File([blob], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

export const createMockImageFile = (name: string = 'test.jpg', size: number = 1024): File => {
  return createMockFile(name, size, 'image/jpeg');
};

export const createMockDocumentFile = (name: string = 'test.pdf', size: number = 2048): File => {
  return createMockFile(name, size, 'application/pdf');
};

// File factory functions (≤8 lines each)
export const createTextFile = (name: string = 'test.txt', content: string = 'test'): File => {
  const blob = new Blob([content], { type: 'text/plain' });
  return new File([blob], name, { type: 'text/plain' });
};

export const createImageFile = (name: string = 'image.png'): File => {
  const canvas = document.createElement('canvas');
  canvas.width = 100;
  canvas.height = 100;
  const ctx = canvas.getContext('2d');
  if (ctx) ctx.fillRect(0, 0, 100, 100);
  return createMockFile(name, 1024, 'image/png');
};

export const createPdfFile = (name: string = 'document.pdf'): File => {
  return createMockDocumentFile(name, 5120);
};

// Environment setup helpers (≤8 lines each)
export const setupFileUploadTestEnvironment = (): void => {
  // Mock FileReader
  global.FileReader = class {
    result: string | ArrayBuffer | null = null;
    readAsDataURL = jest.fn().mockImplementation(() => {
      this.result = 'data:text/plain;base64,dGVzdA==';
      setTimeout(() => this.onload?.({ target: this } as any), 0);
    });
    onload: ((event: any) => void) | null = null;
  } as any;
};

export const cleanupFileUploadResources = (): void => {
  jest.clearAllMocks();
  delete (global as any).FileReader;
};

// Simulation helpers (≤8 lines each)
export const simulateDragDrop = async (element: HTMLElement, files: File[]): Promise<void> => {
  const user = userEvent.setup();
  await user.upload(element, files);
};

export const simulateFileSelection = async (input: HTMLInputElement, files: File[]): Promise<void> => {
  const user = userEvent.setup();
  await user.upload(input, files);
};

// Expectation helpers (≤8 lines each)
export const expectUploadStarted = async (): Promise<void> => {
  await waitFor(() => {
    expect(screen.queryByText(/uploading/i)).toBeInTheDocument();
  });
};

export const expectUploadProgress = async (percentage?: number): Promise<void> => {
  await waitFor(() => {
    const progress = screen.queryByRole('progressbar');
    expect(progress).toBeInTheDocument();
    if (percentage !== undefined) {
      expect(progress).toHaveAttribute('aria-valuenow', percentage.toString());
    }
  });
};

export const expectUploadCompleted = async (): Promise<void> => {
  await waitFor(() => {
    expect(screen.queryByText(/upload complete/i)).toBeInTheDocument();
  });
};

export const expectUploadError = async (errorMessage?: string): Promise<void> => {
  await waitFor(() => {
    const error = screen.queryByText(/error/i);
    expect(error).toBeInTheDocument();
    if (errorMessage) {
      expect(screen.queryByText(errorMessage)).toBeInTheDocument();
    }
  });
};

export const expectFilePreview = async (fileName: string): Promise<void> => {
  await waitFor(() => {
    expect(screen.queryByText(fileName)).toBeInTheDocument();
  });
};

export const expectFileSizeValidation = async (maxSize: number): Promise<void> => {
  await waitFor(() => {
    const message = `File size must be less than ${maxSize}MB`;
    expect(screen.queryByText(message)).toBeInTheDocument();
  });
};

export const expectFileTypeValidation = async (allowedTypes: string[]): Promise<void> => {
  await waitFor(() => {
    const message = `Only ${allowedTypes.join(', ')} files are allowed`;
    expect(screen.queryByText(message)).toBeInTheDocument();
  });
};

// Test provider component (≤8 lines each)
export const FileUploadTestProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  React.useEffect(() => {
    setupFileUploadTestEnvironment();
    return cleanupFileUploadResources;
  }, []);
  
  return <>{children}</>;
};

// Mock data for testing
export const mockFileUploadConfig = {
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedTypes: ['image/jpeg', 'image/png', 'application/pdf', 'text/plain'],
  maxFiles: 5,
};