/**
 * Mock for remark-math
 * 
 * Provides a mock implementation of the math plugin for remark
 */

// Mock plugin function that remark-math exports as default
const remarkMath = () => {
  return (tree) => {
    // Mock transformer function - in real plugin, this would transform math expressions
    // For testing, we just return the tree unchanged
    return tree;
  };
};

// Mock plugin metadata
remarkMath.pluginId = 'remark-math';

module.exports = remarkMath;
module.exports.default = remarkMath;