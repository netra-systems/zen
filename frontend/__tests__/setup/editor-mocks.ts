/**
 * Editor Mocks for Testing
 * Provides mock implementations for Monaco Editor and related components
 */

import { jest } from '@jest/globals';

export function setupMonacoEnvironment() {
  // Mock Monaco Editor
  const mockEditor = {
    create: jest.fn(() => ({
      getValue: jest.fn(() => ''),
      setValue: jest.fn(),
      onDidChangeModelContent: jest.fn(),
      dispose: jest.fn(),
      getModel: jest.fn(() => ({
        getLineCount: jest.fn(() => 1),
        getLineContent: jest.fn(() => ''),
      })),
      updateOptions: jest.fn(),
      layout: jest.fn(),
    })),
    defineTheme: jest.fn(),
    setTheme: jest.fn(),
    createModel: jest.fn(),
  };
  
  // Mock Monaco namespace
  global.monaco = {
    editor: mockEditor,
    languages: {
      register: jest.fn(),
      setLanguageConfiguration: jest.fn(),
      setTokensProvider: jest.fn(),
      registerCompletionItemProvider: jest.fn(),
    },
    Range: jest.fn(),
    Position: jest.fn(),
  };
  
  return mockEditor;
}

export function mockCodeEditor() {
  return {
    value: '',
    language: 'javascript',
    theme: 'vs-dark',
    onChange: jest.fn(),
    onMount: jest.fn(),
    options: {},
  };
}

export function cleanupMonacoMocks() {
  delete global.monaco;
  jest.clearAllMocks();
}