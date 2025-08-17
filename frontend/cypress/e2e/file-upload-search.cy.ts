import {
  setupAuthentication,
  mockReferencesEndpoint,
  openReferencesPanel,
  verifyFileInList,
  verifyFileNotInList,
  ReferenceData
} from '../support/file-upload-utilities';

describe('File Upload Search Features', () => {
  beforeEach(() => {
    setupAuthentication();
    cy.visit('/chat');
  });

  it('should search references by filename and keywords', () => {
    const references = createTestReferences();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    // Test filename search
    searchByKeyword('pdf');
    verifyFileInList('optimization-guide.pdf');
    verifyFileNotInList('performance-metrics.csv');

    // Test keyword search
    searchByKeyword('optimization');
    verifyFileInList('optimization-strategies.pdf');
    verifyFileNotInList('system-architecture.md');

    clearSearch();
    verifyAllReferencesVisible();
  });

  it('should handle case-insensitive and partial search', () => {
    const references = createMixedCaseReferences();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    // Test case-insensitive
    searchByKeyword('PDF');
    verifyFileInList('Document.PDF');
    verifyFileNotInList('optimization-guide.txt');

    // Test partial matches
    searchByKeyword('opt');
    verifyFileInList('optimization-guide.pdf');
    verifyFileInList('options-config.json');

    clearSearch();
  });

  it('should handle edge cases and maintain state', () => {
    const references = createLimitedReferences();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    searchByKeyword('nonexistent');
    cy.contains('No references found matching "nonexistent"')
      .should('be.visible');

    clearSearch();
    verifyFileInList('single-file.txt');
  });
});

const createTestReferences = (): ReferenceData[] => {
  return [
    {
      id: 'ref-1',
      filename: 'optimization-guide.pdf',
      content_type: 'application/pdf',
      size: 50000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-2', 
      filename: 'performance-metrics.csv',
      content_type: 'text/csv',
      size: 25000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-opt',
      filename: 'optimization-strategies.pdf',
      content_type: 'application/pdf',
      size: 15000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-arch',
      filename: 'system-architecture.md',
      content_type: 'text/markdown',
      size: 12000,
      status: 'completed',
      created_at: new Date().toISOString()
    }
  ];
};

const createMixedCaseReferences = (): ReferenceData[] => {
  return [
    {
      id: 'ref-1',
      filename: 'Document.PDF',
      content_type: 'application/pdf',
      size: 10000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-2',
      filename: 'optimization-guide.txt',
      content_type: 'text/plain',
      size: 5000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-3',
      filename: 'optimization-guide.pdf',
      content_type: 'application/pdf',
      size: 10000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-4',
      filename: 'options-config.json',
      content_type: 'application/json',
      size: 3000,
      status: 'completed',
      created_at: new Date().toISOString()
    }
  ];
};

const createLimitedReferences = (): ReferenceData[] => {
  return [
    {
      id: 'ref-only',
      filename: 'single-file.txt',
      content_type: 'text/plain',
      size: 5000,
      status: 'completed',
      created_at: new Date().toISOString()
    }
  ];
};

const searchByKeyword = (keyword: string): void => {
  cy.get('input[placeholder="Search references..."]').clear().type(keyword);
};

const clearSearch = (): void => {
  cy.get('input[placeholder="Search references..."]').clear();
};

const verifyAllReferencesVisible = (): void => {
  verifyFileInList('optimization-guide.pdf');
  verifyFileInList('performance-metrics.csv');
  verifyFileInList('optimization-strategies.pdf');
  verifyFileInList('system-architecture.md');
};