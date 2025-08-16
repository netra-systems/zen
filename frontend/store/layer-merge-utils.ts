/**
 * Layer Merge Utilities
 * 
 * Extracted from unified-chat.ts to maintain 300-line file limit
 * Provides specialized merging logic for different layer types
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed merge utilities
 */

// ============================================
// Helper Functions (8 lines max each)
// ============================================

/**
 * Checks if current partial content is contained in update
 */
const isPartialContentIncluded = (
  current: string,
  update: string
): boolean => {
  return update.includes(current);
};

/**
 * Merges partial content with update content
 */
const mergePartialContent = (
  current: string,
  update: string
): string => {
  return isPartialContentIncluded(current, update)
    ? update
    : current + update;
};

/**
 * Extracts and processes partial content from layer data
 */
const processPartialContent = (
  current: any,
  update: any
): string => {
  const currentPartial = current.partialContent || '';
  return update.partialContent 
    ? mergePartialContent(currentPartial, update.partialContent)
    : currentPartial;
};

/**
 * Extracts and merges completed agents arrays
 */
const mergeCompletedAgents = (
  current: any,
  update: any
): any[] => {
  const currentAgents = current.completedAgents || [];
  return update.completedAgents 
    ? [...currentAgents, ...update.completedAgents]
    : currentAgents;
};

// ============================================
// Main Merge Functions (8 lines max each)
// ============================================

/**
 * Merges medium layer content with special partial content handling
 */
export const mergeMediumLayerContent = (current: any, update: any) => {
  if (!current) return update;
  
  const partialContent = processPartialContent(current, update);
  return { ...current, ...update, partialContent };
};

/**
 * Merges slow layer data with completed agents aggregation
 */
export const mergeSlowLayerAgents = (current: any, update: any) => {
  if (!current) return update;
  
  const completedAgents = mergeCompletedAgents(current, update);
  return { ...current, ...update, completedAgents };
};

/**
 * Creates updated fast layer data with agent name sync
 */
export const createUpdatedFastLayerData = (
  currentFastLayer: any,
  agentName: string | null
): any => {
  return currentFastLayer
    ? { ...currentFastLayer, agentName: agentName || '' }
    : currentFastLayer;
};