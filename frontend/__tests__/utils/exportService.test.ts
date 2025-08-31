/**
 * @jest-environment jsdom
 */

import { ExportService, ExportFormat } from '@/utils/exportService';

// Mock the dependencies
jest.mock('html2canvas', () => {
  return jest.fn().mockImplementation(() => Promise.resolve({
    toBlob: jest.fn((callback) => {
      callback(new Blob(['image data'], { type: 'image/png' }));
    })
  }));
});

// Create a mock jsPDF constructor
const mockJsPDFInstance = {
  setFontSize: jest.fn(),
  setTextColor: jest.fn(),
  text: jest.fn(),
  splitTextToSize: jest.fn((text: string) => [text]),
  addPage: jest.fn(),
  save: jest.fn(),
  internal: {
    pageSize: {
      getHeight: jest.fn(() => 297),
      getWidth: jest.fn(() => 210)
    }
  },
  autoTable: jest.fn(),
  lastAutoTable: { finalY: 100 }
};

const mockJsPDFConstructor = jest.fn(() => mockJsPDFInstance);

jest.mock('jspdf', () => ({
  __esModule: true,
  default: mockJsPDFConstructor
}));
jest.mock('papaparse', () => ({
  unparse: jest.fn((data) => {
    // Simple CSV generation for testing
    if (!data || data.length === 0) return '';
    const headers = Object.keys(data[0]);
    const rows = data.map(row => Object.values(row).join(','));
    return [headers.join(','), ...rows].join('\n');
  })
}));

describe('ExportService', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  // Mock DOM methods
  let createElementSpy: jest.SpyInstance;
  let createObjectURLSpy: jest.SpyInstance;
  let revokeObjectURLSpy: jest.SpyInstance;
  let appendChildSpy: jest.SpyInstance;
  let removeChildSpy: jest.SpyInstance;
  let clickSpy: jest.Mock;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Mock DOM methods
    clickSpy = jest.fn();
    
    // Store the original createElement
    const originalCreateElement = document.createElement.bind(document);
    
    createElementSpy = jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const element = originalCreateElement(tag);
      if (tag === 'a') {
        Object.defineProperty(element, 'click', { 
          value: clickSpy,
          writable: true,
          configurable: true
        });
      }
      return element;
    });

    // Mock URL methods
    createObjectURLSpy = jest.fn().mockReturnValue('blob:mock-url');
    revokeObjectURLSpy = jest.fn();
    
    // Mock URL methods on the global object
    Object.defineProperty(global.URL, 'createObjectURL', {
      value: createObjectURLSpy,
      writable: true,
      configurable: true
    });
    
    Object.defineProperty(global.URL, 'revokeObjectURL', {
      value: revokeObjectURLSpy,
      writable: true,
      configurable: true
    });
    
    appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation((node) => node as any);
    removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation((node) => node as any);

    // Mock Blob constructor
    global.Blob = jest.fn((content, options) => ({
      content,
      type: options?.type || 'text/plain',
      size: content[0]?.length || 0,
      slice: jest.fn(),
      stream: jest.fn(),
      text: jest.fn(),
      arrayBuffer: jest.fn()
    })) as any;
  });

  afterEach(() => {
    // Restore all mocks
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('exportReport', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    const mockReportData = {
      title: 'Test Report',
      summary: 'This is a test summary',
      sections: [
        { title: 'Section 1', content: 'Content 1', type: 'text' as const },
        { title: 'Section 2', content: [{ a: 1, b: 2 }], type: 'table' as const }
      ],
      recommendations: ['Recommendation 1', 'Recommendation 2'],
      metrics: { accuracy: 95, performance: 88 },
      timestamp: Date.now()
    };

    describe('JSON export', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should export report as JSON', async () => {
        await ExportService.exportReport(mockReportData, {
          format: 'json',
          filename: 'test-report'
        });

        expect(Blob).toHaveBeenCalled();
        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = JSON.parse(blobCall[0][0]);
        
        expect(content.title).toBe('Test Report');
        expect(content.summary).toBe('This is a test summary');
        expect(content.sections).toHaveLength(2);
        expect(clickSpy).toHaveBeenCalled();
      });

      it('should include metadata when requested', async () => {
        await ExportService.exportReport(mockReportData, {
          format: 'json',
          filename: 'test-report',
          includeMetadata: true
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = JSON.parse(blobCall[0][0]);
        
        expect(content.metadata).toBeDefined();
        expect(content.metadata.exportedAt).toBeDefined();
        expect(content.metadata.version).toBe('1.0');
        expect(content.metadata.format).toBe('json');
      });

      it('should handle empty report data', async () => {
        await ExportService.exportReport({}, {
          format: 'json'
        });

        expect(Blob).toHaveBeenCalled();
        expect(clickSpy).toHaveBeenCalled();
      });
    });

    describe('CSV export', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should export report as CSV', async () => {
        await ExportService.exportReport(mockReportData, {
          format: 'csv',
          filename: 'test-report'
        });

        expect(Blob).toHaveBeenCalled();
        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        expect(content).toContain('Category');
        expect(content).toContain('Metrics');
        expect(content).toContain('Recommendation');
        expect(clickSpy).toHaveBeenCalled();
      });

      it('should handle complex nested data in CSV', async () => {
        const complexData = {
          ...mockReportData,
          metrics: {
            performance: {
              cpu: 80,
              memory: 60,
              nested: { deep: 'value' }
            }
          }
        };

        await ExportService.exportReport(complexData, {
          format: 'csv'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        // Should stringify complex objects
        expect(content).toContain('{"cpu":80,"memory":60,"nested":{"deep":"value"}}');
      });

      it('should handle sections with table data', async () => {
        const tableData = {
          sections: [{
            title: 'Data Table',
            content: [
              { name: 'Alice', score: 95 },
              { name: 'Bob', score: 87 }
            ],
            type: 'table' as const
          }]
        };

        await ExportService.exportReport(tableData, {
          format: 'csv'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        expect(content).toContain('Data Table');
        expect(content).toContain('Alice');
        expect(content).toContain('Bob');
      });
    });

    describe('Markdown export', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should export report as Markdown', async () => {
        await ExportService.exportReport(mockReportData, {
          format: 'markdown',
          filename: 'test-report'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        expect(content).toContain('# Test Report');
        expect(content).toContain('## Executive Summary');
        expect(content).toContain('## Section 1');
        expect(content).toContain('## Recommendations');
        expect(content).toContain('## Metrics');
        expect(content).toContain('*Generated by Netra AI Optimization Platform*');
      });

      it('should format tables in Markdown', async () => {
        const tableData = {
          sections: [{
            title: 'Results',
            content: [
              { metric: 'Speed', value: '100ms', status: 'Good' },
              { metric: 'Memory', value: '512MB', status: 'OK' }
            ],
            type: 'table' as const
          }]
        };

        await ExportService.exportReport(tableData, {
          format: 'markdown'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        // Check for markdown table format
        expect(content).toContain('| metric | value | status |');
        expect(content).toContain('| --- | --- | --- |');
        expect(content).toContain('| Speed | 100ms | Good |');
        expect(content).toContain('| Memory | 512MB | OK |');
      });

      it('should handle code blocks for non-string content', async () => {
        const codeData = {
          sections: [{
            title: 'Config',
            content: { key: 'value', nested: { prop: true } }
          }]
        };

        await ExportService.exportReport(codeData, {
          format: 'markdown'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        expect(content).toContain('```json');
        expect(content).toContain('"key": "value"');
        expect(content).toContain('"nested": {');
        expect(content).toContain('```');
      });

      it('should include recommendations with descriptions', async () => {
        const recData = {
          recommendations: [
            { title: 'Optimize Database', description: 'Add indexes to improve query performance' },
            { title: 'Cache Results', description: 'Implement Redis caching' }
          ]
        };

        await ExportService.exportReport(recData, {
          format: 'markdown'
        });

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        const content = blobCall[0][0];
        
        expect(content).toContain('1. Optimize Database');
        expect(content).toContain('   Add indexes to improve query performance');
        expect(content).toContain('2. Cache Results');
        expect(content).toContain('   Implement Redis caching');
      });
    });

    describe('PDF export', () => {

          setupAntiHang();

        jest.setTimeout(10000);

      it('should export report as PDF', async () => {
        // Clear previous calls
        mockJsPDFConstructor.mockClear();
        Object.values(mockJsPDFInstance).forEach((mock: any) => {
          if (typeof mock === 'function' && mock.mockClear) {
            mock.mockClear();
          }
        });

        await ExportService.exportReport(mockReportData, {
          format: 'pdf',
          filename: 'test-report'
        });

        expect(mockJsPDFConstructor).toHaveBeenCalled();
        expect(mockJsPDFInstance.setFontSize).toHaveBeenCalled();
        expect(mockJsPDFInstance.text).toHaveBeenCalled();
        expect(mockJsPDFInstance.save).toHaveBeenCalledWith('test-report.pdf');
      });

      it('should include custom branding in PDF', async () => {
        // Clear previous calls
        mockJsPDFConstructor.mockClear();
        Object.values(mockJsPDFInstance).forEach((mock: any) => {
          if (typeof mock === 'function' && mock.mockClear) {
            mock.mockClear();
          }
        });

        await ExportService.exportReport(mockReportData, {
          format: 'pdf',
          customBranding: {
            companyName: 'Test Company',
            primaryColor: '#10B981'
          }
        });

        // Check that company name was added
        const textCalls = mockJsPDFInstance.text.mock.calls;
        const companyNameCall = textCalls.find((call: any[]) => 
          call[0] === 'Test Company'
        );
        expect(companyNameCall).toBeDefined();
      });
    });

    describe('Error handling', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should throw error for unsupported format', async () => {
        await expect(
          ExportService.exportReport(mockReportData, {
            format: 'unsupported' as ExportFormat
          })
        ).rejects.toThrow('Unsupported export format: unsupported');
      });

      it('should generate filename if not provided', async () => {
        const dateSpy = jest.spyOn(Date.prototype, 'toISOString')
          .mockReturnValue('2024-01-15T10:30:45.123Z');

        await ExportService.exportReport(
          { title: 'Auto Named Report' },
          { format: 'json' }
        );

        const blobCall = (Blob as jest.Mock).mock.calls[0];
        expect(blobCall).toBeDefined();
        
        // Check that a filename was generated
        const anchorElement = createElementSpy.mock.results.find(
          r => r.value?.tagName === 'A'
        )?.value;
        expect(anchorElement?.download).toContain('auto_named_report');
        expect(anchorElement?.download).toContain('2024-01-15');

        dateSpy.mockRestore();
      });

      it('should sanitize filename', async () => {
        await ExportService.exportReport(
          { title: 'Report with Special!@# Chars' },
          { format: 'json' }
        );

        const anchorElement = createElementSpy.mock.results.find(
          r => r.value?.tagName === 'A'
        )?.value;
        
        // Special characters should be replaced with underscores
        expect(anchorElement?.download).toMatch(/^report_with_special____chars_/);
      });
    });
  });

  describe('exportElementAsImage', () => {

        setupAntiHang();

      jest.setTimeout(10000);

    it('should export element as image', async () => {
      const mockElement = document.createElement('div');
      mockElement.id = 'test-element';
      document.body.appendChild(mockElement);

      jest.spyOn(document, 'getElementById').mockReturnValue(mockElement);

      await ExportService.exportElementAsImage('test-element', 'screenshot');

      const html2canvasMock = require('html2canvas');
      expect(html2canvasMock).toHaveBeenCalledWith(mockElement);
      expect(clickSpy).toHaveBeenCalled();

      document.body.removeChild(mockElement);
    });

    it('should throw error if element not found', async () => {
      jest.spyOn(document, 'getElementById').mockReturnValue(null);

      await expect(
        ExportService.exportElementAsImage('nonexistent', 'screenshot')
      ).rejects.toThrow('Element with id nonexistent not found');
    });

    it('should use default filename if not provided', async () => {
      const mockElement = document.createElement('div');
      mockElement.id = 'test-element';
      document.body.appendChild(mockElement);
      
      jest.spyOn(document, 'getElementById').mockReturnValue(mockElement);

      await ExportService.exportElementAsImage('test-element');

      const anchorElement = createElementSpy.mock.results.find(
        r => r.value?.tagName === 'A'
      )?.value;
      
      expect(anchorElement?.download).toBe('export.png');
      
      document.body.removeChild(mockElement);
    });
  });

  describe('Utility methods', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should handle download cleanup properly', async () => {
      await ExportService.exportReport(
        { title: 'Test' },
        { format: 'json' }
      );

      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(appendChildSpy).toHaveBeenCalled();
      expect(clickSpy).toHaveBeenCalled();
      expect(removeChildSpy).toHaveBeenCalled();
      expect(revokeObjectURLSpy).toHaveBeenCalled();
    });

    it('should handle large reports efficiently', async () => {
      const largeReport = {
        title: 'Large Report',
        sections: Array.from({ length: 100 }, (_, i) => ({
          title: `Section ${i}`,
          content: `Content for section ${i}`.repeat(100)
        })),
        metrics: Object.fromEntries(
          Array.from({ length: 100 }, (_, i) => [`metric${i}`, Math.random()])
        )
      };

      const startTime = performance.now();
      
      await ExportService.exportReport(largeReport, {
        format: 'json'
      });

      const endTime = performance.now();
      
      // Should complete in reasonable time
      expect(endTime - startTime).toBeLessThan(100);
      expect(Blob).toHaveBeenCalled();
    });

    it('should handle special characters in content', async () => {
      const specialReport = {
        title: 'Special "Characters" & Symbols',
        summary: 'Content with <HTML> tags & "quotes"',
        sections: [{
          title: 'Unicode 😀🎉',
          content: 'Tab\tNewline\nCarriage\rReturn'
        }]
      };

      await ExportService.exportReport(specialReport, {
        format: 'json'
      });

      const blobCall = (Blob as jest.Mock).mock.calls[0];
      const content = JSON.parse(blobCall[0][0]);
      
      expect(content.title).toBe('Special "Characters" & Symbols');
      expect(content.sections[0].title).toBe('Unicode 😀🎉');
    });
  });
});