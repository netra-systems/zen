import {
  setupAuthentication,
  mockEmptyReferences,
  openReferencesPanel,
  createTestFile,
  mockFileUpload,
  mockUploadError,
  uploadSingleFile,
  createStatusUpdate,
  sendWebSocketMessage,
  TestFile
} from '../support/file-upload-utilities';

describe('File Upload Error Handling and Processing Status', () => {
  beforeEach(() => {
    setupAuthentication();
    mockEmptyReferences();
    cy.visit('/chat');
  });

  it('should handle file upload errors gracefully', () => {
    openReferencesPanel();

    mockUploadError(
      413,
      'File too large', 
      'The uploaded file exceeds the maximum size limit of 10MB'
    );

    const largeFile = createLargeTestFile();
    uploadSingleFile(largeFile);
    cy.wait('@uploadError');

    verifyFileTooLargeError();
    dismissError();

    testUnsupportedFileType();
  });

  it('should handle reference processing status updates', () => {
    openReferencesPanel();

    const testFile = createTestFile(
      'complex-document.pdf',
      'content',
      'application/pdf'
    );

    mockFileUpload(testFile, 'ref-processing');
    uploadSingleFile(testFile);
    cy.wait('@uploadFile');

    simulateProcessingStages();
    verifyProcessingComplete();
  });

  it('should handle network errors during upload', () => {
    openReferencesPanel();

    mockNetworkError();

    const testFile = createTestFile(
      'network-test.pdf',
      'test content',
      'application/pdf'
    );

    uploadSingleFile(testFile);
    cy.wait('@networkError');

    verifyNetworkErrorMessage();
    retryUpload();
  });

  it('should handle processing failures', () => {
    openReferencesPanel();

    const testFile = createTestFile(
      'corrupt-file.pdf',
      'corrupted content',
      'application/pdf'
    );

    mockFileUpload(testFile, 'ref-failed');
    uploadSingleFile(testFile);
    cy.wait('@uploadFile');

    simulateProcessingFailure();
    verifyProcessingFailureMessage();
    handleFailureActions();
  });

  it('should handle timeout errors', () => {
    openReferencesPanel();

    mockTimeoutError();

    const testFile = createTestFile(
      'timeout-test.txt',
      'test content',
      'text/plain'
    );

    uploadSingleFile(testFile);
    cy.wait('@timeoutError');

    verifyTimeoutErrorMessage();
  });

  it('should display upload progress correctly', () => {
    openReferencesPanel();

    const testFile = createTestFile(
      'progress-test.pdf',
      'content for progress test',
      'application/pdf'
    );

    mockFileUpload(testFile, 'ref-progress');
    uploadSingleFile(testFile);
    cy.wait('@uploadFile');

    simulateDetailedProgress();
    verifyProgressDisplay();
  });
});

const createLargeTestFile = (): TestFile => {
  const largeContent = 'x'.repeat(11 * 1024 * 1024); // 11MB
  return createTestFile('large-file.pdf', largeContent, 'application/pdf');
};

const verifyFileTooLargeError = (): void => {
  cy.contains('File too large').should('be.visible');
  cy.contains('exceeds the maximum size limit').should('be.visible');
};

const dismissError = (): void => {
  cy.get('button[aria-label="Dismiss error"]').click();
  cy.contains('File too large').should('not.exist');
};

const testUnsupportedFileType = (): void => {
  mockUploadError(
    415,
    'Unsupported file type',
    'Only PDF, TXT, CSV, JSON, and Markdown files are supported'
  );

  const unsupportedFile = createTestFile(
    'file.exe',
    'binary content',
    'application/x-msdownload'
  );

  uploadSingleFile(unsupportedFile);
  cy.wait('@uploadError');

  verifyUnsupportedFileError();
};

const verifyUnsupportedFileError = (): void => {
  cy.contains('Unsupported file type').should('be.visible');
  cy.contains('Only PDF, TXT, CSV, JSON, and Markdown files')
    .should('be.visible');
};

const simulateProcessingStages = (): void => {
  const stages = [
    { 
      status: 'extracting_text', 
      progress: 25, 
      message: 'Extracting text from document...' 
    },
    { 
      status: 'generating_embeddings', 
      progress: 50, 
      message: 'Generating embeddings...' 
    },
    { 
      status: 'indexing', 
      progress: 75, 
      message: 'Indexing content...' 
    },
    { 
      status: 'completed', 
      progress: 100, 
      message: 'Processing complete!' 
    }
  ];

  stages.forEach((stage, index) => {
    cy.wait(index * 1000).then(() => {
      const statusUpdate = createStatusUpdate(
        'ref-processing',
        stage.status,
        stage.progress,
        stage.message
      );
      sendWebSocketMessage(statusUpdate);
    });
  });
};

const verifyProcessingComplete = (): void => {
  cy.contains('Processing complete!').should('be.visible');
  cy.contains('100%').should('be.visible');
  
  cy.contains('complex-document.pdf').parent()
    .should('not.have.class', 'opacity-50');
  
  cy.get('input[type="checkbox"][value="ref-processing"]')
    .should('not.be.disabled');
};

const mockNetworkError = (): void => {
  cy.intercept('POST', '/api/references/upload', {
    forceNetworkError: true
  }).as('networkError');
};

const verifyNetworkErrorMessage = (): void => {
  cy.contains('Network error').should('be.visible');
  cy.contains('Please check your connection').should('be.visible');
};

const retryUpload = (): void => {
  cy.get('button').contains('Retry').click();
};

const simulateProcessingFailure = (): void => {
  const failureUpdate = createStatusUpdate(
    'ref-failed',
    'failed',
    0,
    'Processing failed: Unable to extract text from file'
  );
  
  sendWebSocketMessage(failureUpdate);
};

const verifyProcessingFailureMessage = (): void => {
  cy.contains('Processing failed').should('be.visible');
  cy.contains('Unable to extract text').should('be.visible');
};

const handleFailureActions = (): void => {
  cy.get('button').contains('Remove').should('be.visible');
  cy.get('button').contains('Retry').should('be.visible');
};

const mockTimeoutError = (): void => {
  cy.intercept('POST', '/api/references/upload', (req) => {
    req.destroy();
  }).as('timeoutError');
};

const verifyTimeoutErrorMessage = (): void => {
  cy.contains('Upload timeout').should('be.visible');
  cy.contains('The upload took too long').should('be.visible');
};

const simulateDetailedProgress = (): void => {
  const progressStages = [
    { progress: 10, message: 'Uploading...' },
    { progress: 25, message: 'Extracting text...' },
    { progress: 50, message: 'Generating embeddings...' },
    { progress: 75, message: 'Indexing content...' },
    { progress: 100, message: 'Complete!' }
  ];

  progressStages.forEach((stage, index) => {
    cy.wait(index * 500).then(() => {
      const progressUpdate = createStatusUpdate(
        'ref-progress',
        'processing',
        stage.progress,
        stage.message
      );
      sendWebSocketMessage(progressUpdate);
    });
  });
};

const verifyProgressDisplay = (): void => {
  cy.contains('Uploading...').should('be.visible');
  cy.contains('Extracting text...').should('be.visible');
  cy.contains('Generating embeddings...').should('be.visible');
  cy.contains('Indexing content...').should('be.visible');
  cy.contains('Complete!').should('be.visible');
};