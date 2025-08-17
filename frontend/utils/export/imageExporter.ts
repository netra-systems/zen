/**
 * Image Exporter - Handles image export functionality
 * Converts DOM elements to downloadable images
 */

import html2canvas from 'html2canvas';
import { downloadBlob } from './exportUtils';

/**
 * Export DOM element as image
 */
export async function exportElementAsImage(
  elementId: string,
  filename?: string
): Promise<void> {
  const element = getElementById(elementId);
  const canvas = await createCanvasFromElement(element);
  const blob = await createBlobFromCanvas(canvas);
  downloadBlob(blob, `${filename || 'export'}.png`);
}

/**
 * Get element by ID with validation
 */
function getElementById(elementId: string): HTMLElement {
  const element = document.getElementById(elementId);
  if (!element) {
    throw new Error(`Element with id ${elementId} not found`);
  }
  return element;
}

/**
 * Create canvas from DOM element
 */
async function createCanvasFromElement(element: HTMLElement): Promise<HTMLCanvasElement> {
  return await html2canvas(element);
}

/**
 * Create blob from canvas
 */
async function createBlobFromCanvas(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise<Blob>((resolve) => {
    canvas.toBlob((blob) => resolve(blob!), 'image/png');
  });
}

/**
 * Export multiple elements as images
 */
export async function exportMultipleElementsAsImages(
  elementIds: string[],
  baseFilename?: string
): Promise<void> {
  for (const [index, elementId] of elementIds.entries()) {
    const filename = baseFilename 
      ? `${baseFilename}_${index + 1}` 
      : `export_${index + 1}`;
    await exportElementAsImage(elementId, filename);
  }
}

/**
 * Export element with custom options
 */
export async function exportElementWithOptions(
  elementId: string,
  options: {
    filename?: string;
    format?: 'png' | 'jpeg';
    quality?: number;
    scale?: number;
  }
): Promise<void> {
  const element = getElementById(elementId);
  const canvas = await html2canvas(element, {
    scale: options.scale || 1
  });
  
  const format = options.format === 'jpeg' ? 'image/jpeg' : 'image/png';
  const quality = options.quality || 0.9;
  
  const blob = await new Promise<Blob>((resolve) => {
    canvas.toBlob((blob) => resolve(blob!), format, quality);
  });
  
  const extension = options.format === 'jpeg' ? 'jpg' : 'png';
  downloadBlob(blob, `${options.filename || 'export'}.${extension}`);
}