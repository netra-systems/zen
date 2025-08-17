import {
  setupAuthentication,
  mockReferencesEndpoint,
  openReferencesPanel,
  mockPreviewContent,
  verifyFileInList,
  verifyFileNotInList,
  ReferenceData
} from '../support/file-upload-utilities';

describe('File Upload Advanced Search Features', () => {
  beforeEach(() => {
    setupAuthentication();
    cy.visit('/chat');
  });

  it('should preview reference content', () => {
    const reference = createTextReference();
    mockReferencesEndpoint([reference]);
    mockPreviewContent(reference.id, 'Sample preview content...');
    
    openReferencesPanel();
    clickPreviewButton(reference.filename);
    cy.wait('@getPreview');

    verifyPreviewModal(reference.filename);
    closePreview();
  });

  it('should sort references by different criteria', () => {
    const references = createReferencesWithDates();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    sortByName();
    verifyNameSortOrder();

    sortByDate();
    verifyDateSortOrder();

    sortBySize();
    verifySizeSortOrder();
  });

  it('should handle advanced search combinations', () => {
    const references = createAdvancedSearchReferences();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    performAdvancedSearch();
    verifyAdvancedSearchResults();
  });

  it('should preview different file types correctly', () => {
    const references = createMultiTypeReferences();
    mockReferencesEndpoint(references);
    setupPreviewMocks();
    
    openReferencesPanel();
    
    testPdfPreview();
    testJsonPreview();
    testCsvPreview();
  });

  it('should handle preview errors gracefully', () => {
    const reference = createLargeReference();
    mockReferencesEndpoint([reference]);
    mockPreviewError(reference.id);
    
    openReferencesPanel();
    clickPreviewButton(reference.filename);
    cy.wait('@getPreviewError');

    verifyPreviewErrorMessage();
  });

  it('should support sorting with pagination', () => {
    const references = createLargeReferenceSet();
    mockReferencesEndpoint(references);
    openReferencesPanel();

    enablePagination();
    sortBySize();
    verifyPaginatedSortOrder();

    navigateToNextPage();
    verifySortOrderMaintained();
  });
});

const createTextReference = (): ReferenceData => {
  return {
    id: 'ref-1',
    filename: 'sample.txt',
    content_type: 'text/plain',
    size: 1000,
    status: 'completed',
    created_at: new Date().toISOString()
  };
};

const createReferencesWithDates = (): ReferenceData[] => {
  const now = new Date();
  return [
    {
      id: 'ref-1',
      filename: 'a-first.pdf',
      content_type: 'application/pdf',
      size: 10000,
      status: 'completed',
      created_at: new Date(now.getTime() - 86400000).toISOString()
    },
    {
      id: 'ref-2', 
      filename: 'z-last.txt',
      content_type: 'text/plain',
      size: 50000,
      status: 'completed',
      created_at: now.toISOString()
    }
  ];
};

const createAdvancedSearchReferences = (): ReferenceData[] => {
  return [
    {
      id: 'ref-recent-pdf',
      filename: 'recent-analysis.pdf',
      content_type: 'application/pdf',
      size: 25000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-old-txt',
      filename: 'old-notes.txt',
      content_type: 'text/plain',
      size: 8000,
      status: 'completed',
      created_at: new Date(Date.now() - 604800000).toISOString()
    }
  ];
};

const createMultiTypeReferences = (): ReferenceData[] => {
  return [
    {
      id: 'ref-pdf',
      filename: 'document.pdf',
      content_type: 'application/pdf',
      size: 15000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-json',
      filename: 'config.json',
      content_type: 'application/json',
      size: 2000,
      status: 'completed',
      created_at: new Date().toISOString()
    },
    {
      id: 'ref-csv',
      filename: 'data.csv',
      content_type: 'text/csv',
      size: 8000,
      status: 'completed',
      created_at: new Date().toISOString()
    }
  ];
};

const createLargeReference = (): ReferenceData => {
  return {
    id: 'ref-large',
    filename: 'huge-document.pdf',
    content_type: 'application/pdf',
    size: 50000000, // 50MB
    status: 'completed',
    created_at: new Date().toISOString()
  };
};

const createLargeReferenceSet = (): ReferenceData[] => {
  return Array.from({ length: 25 }, (_, i) => ({
    id: `ref-${i + 1}`,
    filename: `file-${i + 1}.pdf`,
    content_type: 'application/pdf',
    size: Math.floor(Math.random() * 100000) + 1000,
    status: 'completed',
    created_at: new Date(Date.now() - i * 86400000).toISOString()
  }));
};

const clickPreviewButton = (filename: string): void => {
  cy.contains(filename).parent().find('button[aria-label="Preview"]').click();
};

const verifyPreviewModal = (filename: string): void => {
  cy.contains(`Preview: ${filename}`).should('be.visible');
  cy.contains('Sample preview content').should('be.visible');
};

const closePreview = (): void => {
  cy.get('button[aria-label="Close preview"]').click();
  cy.contains('Preview:').should('not.exist');
};

const sortByName = (): void => {
  cy.get('button[aria-label="Sort by name"]').click();
};

const verifyNameSortOrder = (): void => {
  cy.get('[data-testid="reference-item"]').first()
    .should('contain', 'a-first.pdf');
};

const sortByDate = (): void => {
  cy.get('button[aria-label="Sort by date"]').click();
};

const verifyDateSortOrder = (): void => {
  cy.get('[data-testid="reference-item"]').first()
    .should('contain', 'z-last.txt');
};

const sortBySize = (): void => {
  cy.get('button[aria-label="Sort by size"]').click();
};

const verifySizeSortOrder = (): void => {
  cy.get('[data-testid="reference-item"]').first()
    .should('contain', 'z-last.txt');
};

const performAdvancedSearch = (): void => {
  cy.get('button[aria-label="Advanced search"]').click();
  cy.get('select[name="fileType"]').select('application/pdf');
  cy.get('select[name="dateRange"]').select('last-week');
  cy.get('input[name="minSize"]').type('20000');
};

const verifyAdvancedSearchResults = (): void => {
  verifyFileInList('recent-analysis.pdf');
  verifyFileNotInList('old-notes.txt');
};

const setupPreviewMocks = (): void => {
  mockPreviewContent('ref-pdf', 'PDF document content preview...');
  mockPreviewContent('ref-json', '{"configuration": "preview"}');
  mockPreviewContent('ref-csv', 'Name,Value\nItem1,100\nItem2,200');
};

const testPdfPreview = (): void => {
  clickPreviewButton('document.pdf');
  cy.wait('@getPreview');
  cy.contains('PDF document content').should('be.visible');
  closePreview();
};

const testJsonPreview = (): void => {
  clickPreviewButton('config.json');
  cy.wait('@getPreview');
  cy.contains('configuration').should('be.visible');
  closePreview();
};

const testCsvPreview = (): void => {
  clickPreviewButton('data.csv');
  cy.wait('@getPreview');
  cy.contains('Name,Value').should('be.visible');
  closePreview();
};

const mockPreviewError = (referenceId: string): void => {
  cy.intercept(`GET`, `/api/references/${referenceId}/preview`, {
    statusCode: 413,
    body: {
      error: 'File too large for preview',
      message: 'File exceeds preview size limit'
    }
  }).as('getPreviewError');
};

const verifyPreviewErrorMessage = (): void => {
  cy.contains('File too large for preview').should('be.visible');
  cy.contains('exceeds preview size limit').should('be.visible');
};

const enablePagination = (): void => {
  cy.get('select[aria-label="Items per page"]').select('10');
};

const verifyPaginatedSortOrder = (): void => {
  cy.get('[data-testid="reference-item"]').should('have.length', 10);
  cy.get('[data-testid="reference-item"]').first()
    .should('contain', 'file-');
};

const navigateToNextPage = (): void => {
  cy.get('button[aria-label="Next page"]').click();
};

const verifySortOrderMaintained = (): void => {
  cy.get('[data-testid="reference-item"]').should('have.length', 10);
  cy.get('[data-testid="reference-item"]').first()
    .should('contain', 'file-');
};