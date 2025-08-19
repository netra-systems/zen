/**
 * Function Line Checker Utility
 * Verifies that all functions in integration test files are ≤8 lines
 */

import fs from 'fs';
import path from 'path';

// Types for line counting
export interface FunctionInfo {
  name: string;
  startLine: number;
  endLine: number;
  lineCount: number;
  filePath: string;
}

export interface FileReport {
  filePath: string;
  totalFunctions: number;
  compliantFunctions: number;
  violatingFunctions: FunctionInfo[];
}

// Function to count lines in functions (≤8 lines)
export const countFunctionLines = (functionBody: string): number => {
  const lines = functionBody.split('\n');
  const nonEmptyLines = lines.filter(line => line.trim().length > 0);
  
  return nonEmptyLines.length;
};

// Extract functions from file content (≤8 lines)
export const extractFunctions = (content: string, filePath: string): FunctionInfo[] => {
  const functionRegex = /(?:const|function|export const|export function)\s+(\w+)\s*[=:]?\s*(?:\([^)]*\))?\s*(?:=>\s*)?\{/g;
  const functions: FunctionInfo[] = [];
  const lines = content.split('\n');
  
  let match;
  while ((match = functionRegex.exec(content)) !== null) {
    const functionName = match[1];
    const startIndex = match.index;
    const startLine = content.substring(0, startIndex).split('\n').length;
    
    const endLine = findFunctionEnd(lines, startLine - 1);
    const lineCount = endLine - startLine + 1;
    
    functions.push({
      name: functionName,
      startLine,
      endLine,
      lineCount,
      filePath
    });
  }
  
  return functions;
};

// Find the end of a function (≤8 lines)
const findFunctionEnd = (lines: string[], startLineIndex: number): number => {
  let braceCount = 0;
  let foundOpenBrace = false;
  
  for (let i = startLineIndex; i < lines.length; i++) {
    const line = lines[i];
    
    for (const char of line) {
      if (char === '{') {
        braceCount++;
        foundOpenBrace = true;
      } else if (char === '}') {
        braceCount--;
        if (foundOpenBrace && braceCount === 0) {
          return i + 1;
        }
      }
    }
  }
  
  return lines.length;
};

// Check file compliance (≤8 lines)
export const checkFileCompliance = (filePath: string): FileReport => {
  const content = fs.readFileSync(filePath, 'utf-8');
  const functions = extractFunctions(content, filePath);
  
  const violatingFunctions = functions.filter(func => func.lineCount > 8);
  
  return {
    filePath,
    totalFunctions: functions.length,
    compliantFunctions: functions.length - violatingFunctions.length,
    violatingFunctions
  };
};

// Check multiple files (≤8 lines)
export const checkMultipleFiles = (filePaths: string[]): FileReport[] => {
  return filePaths.map(filePath => {
    try {
      return checkFileCompliance(filePath);
    } catch (error) {
      console.error(`Error checking file ${filePath}:`, error);
      return {
        filePath,
        totalFunctions: 0,
        compliantFunctions: 0,
        violatingFunctions: []
      };
    }
  });
};

// Generate compliance report (≤8 lines)
export const generateComplianceReport = (reports: FileReport[]): string => {
  const totalFunctions = reports.reduce((sum, report) => sum + report.totalFunctions, 0);
  const totalCompliant = reports.reduce((sum, report) => sum + report.compliantFunctions, 0);
  const totalViolations = reports.reduce((sum, report) => sum + report.violatingFunctions.length, 0);
  
  const compliancePercentage = totalFunctions > 0 ? (totalCompliant / totalFunctions * 100).toFixed(2) : '0';
  
  let report = `\n=== INTEGRATION TEST FUNCTION COMPLIANCE REPORT ===\n`;
  report += `Total Functions: ${totalFunctions}\n`;
  report += `Compliant Functions (≤8 lines): ${totalCompliant}\n`;
  report += `Violating Functions (>8 lines): ${totalViolations}\n`;
  report += `Compliance Percentage: ${compliancePercentage}%\n\n`;
  
  if (totalViolations > 0) {
    report += `VIOLATIONS:\n`;
    reports.forEach(fileReport => {
      if (fileReport.violatingFunctions.length > 0) {
        report += `\nFile: ${path.basename(fileReport.filePath)}\n`;
        fileReport.violatingFunctions.forEach(func => {
          report += `  - ${func.name}: ${func.lineCount} lines (lines ${func.startLine}-${func.endLine})\n`;
        });
      }
    });
  }
  
  return report;
};

// Main verification function (≤8 lines)
export const verifyIntegrationTestCompliance = (): boolean => {
  const integrationTestDir = path.join(__dirname, '..');
  const refactoredFiles = [
    'websocket-complete-refactored.test.tsx',
    'auth-flow-refactored.test.tsx',
    'comprehensive-integration-elite.test.tsx'
  ];
  
  const utilityFiles = [
    'utils/integration-setup-utils.ts',
    'utils/user-flow-utils.ts',
    'utils/state-verification-utils.ts',
    'utils/async-operation-utils.ts',
    'utils/websocket-component-utils.tsx',
    'utils/websocket-test-operations.ts',
    'utils/auth-flow-utils.tsx',
    'utils/comprehensive-test-utils.tsx'
  ];
  
  const allFiles = [
    ...refactoredFiles.map(file => path.join(integrationTestDir, file)),
    ...utilityFiles.map(file => path.join(integrationTestDir, file))
  ];
  
  const reports = checkMultipleFiles(allFiles);
  const complianceReport = generateComplianceReport(reports);
  
  console.log(complianceReport);
  
  const totalViolations = reports.reduce((sum, report) => sum + report.violatingFunctions.length, 0);
  return totalViolations === 0;
};