/**
 * Mock for remark-gfm
 * 
 * Provides a mock implementation of the GitHub Flavored Markdown plugin for remark
 */

// Mock plugin function that remark-gfm exports as default
const remarkGfm = () => {
  return (tree) => {
    // Mock transformer function - in real plugin, this would transform the AST
    // For testing, we just return the tree unchanged
    return tree;
  };
};

// Mock plugin metadata
remarkGfm.pluginId = 'remark-gfm';

module.exports = remarkGfm;
module.exports.default = remarkGfm;