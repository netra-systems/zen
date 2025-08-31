import {
  setupAuthentication,
  mockEmptyReferences,
  openReferencesPanel,
  createTestFile,
  generateFileForUpload,
  mockFileUpload,
  mockProcessingStatus,
  mockReferencesEndpoint,
  uploadSingleFile,
  verifyEmptyState,
  verifyFileInList,
  ReferenceData
} from '../support/file-upload-utilities';

describe('Basic File Upload and Reference Creation', () => {
  beforeEach(() => {
    setupAuthentication();
    mockEmptyReferences();
    // Visit ingestion page where file upload functionality currently exists
    cy.visit('/ingestion');
  });

  it.skip('should upload a file and create a reference - SKIPPED: References panel not in current implementation', () => {
    // This test expects a References button in /chat that doesn't exist in current implementation
    // File upload functionality is now in /ingestion page
    // TODO: Update test when References panel is re-implemented in chat interface
    openReferencesPanel();
    verifyEmptyState();

    const testFile = createTestFile(
      'optimization-guide.pdf',
      'LLM Optimization Best Practices',
      'application/pdf'
    );

    mockFileUpload(testFile, 'ref-1');
    mockProcessingStatus('ref-1');

    uploadSingleFile(testFile);
    cy.wait('@uploadFile');

    verifyUploadProgress(testFile.name);
    cy.wait('@getProcessingStatus');

    const completedReference: ReferenceData = {
      id: 'ref-1',
      filename: testFile.name,
      content_type: testFile.type,
      size: testFile.content.length,
      status: 'completed',
      created_at: new Date().toISOString(),
      metadata: {
        page_count: 10,
        word_count: 5000,
        embeddings_generated: true
      }
    };

    mockReferencesEndpoint([completedReference]);
    cy.wait('@getReferences');

    verifyCompletedUpload(testFile.name);
  });

  it.skip('should upload text file and process correctly - SKIPPED: References panel not in current implementation', () => {
    // This test expects a References button in /chat that doesn't exist in current implementation
    openReferencesPanel();

    const textFile = createTestFile(
      'notes.txt',
      'These are my optimization notes',
      'text/plain'
    );

    mockFileUpload(textFile, 'ref-text');
    mockProcessingStatus('ref-text', {
      word_count: 5,
      embeddings_generated: true
    });

    uploadSingleFile(textFile);
    cy.wait('@uploadFile');

    const completedTextRef: ReferenceData = {
      id: 'ref-text',
      filename: textFile.name,
      content_type: textFile.type,
      size: textFile.content.length,
      status: 'completed',
      created_at: new Date().toISOString(),
      metadata: {
        word_count: 5,
        embeddings_generated: true
      }
    };

    mockReferencesEndpoint([completedTextRef]);
    cy.wait('@getReferences');

    verifyFileInList(textFile.name);
    cy.contains('5 words').should('be.visible');
  });

  it.skip('should upload JSON file and display metadata - SKIPPED: References panel not in current implementation', () => {
    // This test expects a References button in /chat that doesn't exist in current implementation
    openReferencesPanel();

    const jsonFile = createTestFile(
      'config.json',
      '{"optimization": {"enabled": true, "strategy": "aggressive"}}',
      'application/json'
    );

    mockFileUpload(jsonFile, 'ref-json');
    mockProcessingStatus('ref-json', {
      keys_count: 2,
      embeddings_generated: true
    });

    uploadSingleFile(jsonFile);
    cy.wait('@uploadFile');

    const completedJsonRef: ReferenceData = {
      id: 'ref-json',
      filename: jsonFile.name,
      content_type: jsonFile.type,
      size: jsonFile.content.length,
      status: 'completed',
      created_at: new Date().toISOString(),
      metadata: {
        keys_count: 2,
        embeddings_generated: true
      }
    };

    mockReferencesEndpoint([completedJsonRef]);
    cy.wait('@getReferences');

    verifyFileInList(jsonFile.name);
    cy.contains('JSON').should('be.visible');
  });

  it.skip('should upload CSV file and show data info - SKIPPED: References panel not in current implementation', () => {
    // This test expects a References button in /chat that doesn't exist in current implementation
    openReferencesPanel();

    const csvFile = createTestFile(
      'data.csv',
      'name,value\\ntest1,100\\ntest2,200',
      'text/csv'
    );

    mockFileUpload(csvFile, 'ref-csv');
    mockProcessingStatus('ref-csv', {
      row_count: 2,
      column_count: 2,
      embeddings_generated: true
    });

    uploadSingleFile(csvFile);
    cy.wait('@uploadFile');

    const completedCsvRef: ReferenceData = {
      id: 'ref-csv',
      filename: csvFile.name,
      content_type: csvFile.type,
      size: csvFile.content.length,
      status: 'completed',
      created_at: new Date().toISOString(),
      metadata: {
        row_count: 2,
        column_count: 2,
        embeddings_generated: true
      }
    };

    mockReferencesEndpoint([completedCsvRef]);
    cy.wait('@getReferences');

    verifyFileInList(csvFile.name);
    cy.contains('2 rows').should('be.visible');
    cy.contains('2 columns').should('be.visible');
  });

  // New test for current ingestion functionality
  it('should display file upload interface on ingestion page', () => {
    // Verify the ingestion page loads with expected elements
    cy.contains('Data Ingestion').should('be.visible');
    cy.contains('Configure Data Source').should('be.visible');
    
    // Look for file input in the current FileUploadSection implementation
    cy.get('input[type="file"]').should('exist');
    
    // Test file selection
    const testFile = createTestFile(
      'test-document.pdf',
      'Test content for ingestion',
      'application/pdf'
    );
    
    const fileInput = generateFileForUpload(testFile);
    cy.get('input[type="file"]').selectFile(fileInput, { force: true });
    
    // Verify file appears in selected files list (based on FileUploadSection component)
    cy.contains('test-document.pdf').should('be.visible');
    
    // Verify the "Start Ingestion" button is present
    cy.contains('Start Ingestion').should('be.visible');
  });
});

const verifyUploadProgress = (filename: string): void => {
  cy.contains(`Uploading ${filename}`).should('be.visible');
  cy.get('[role="progressbar"]').should('be.visible');
};

const verifyCompletedUpload = (filename: string): void => {
  verifyFileInList(filename);
  cy.contains('10 pages').should('be.visible');
  cy.contains('5000 words').should('be.visible');
};