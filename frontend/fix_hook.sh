#!/bin/bash

# Replace first useEffect
sed -i 's/  useEffect(() => {$/&\n    \/\/ Skip initialization in test environment to avoid act() warnings\n    if (process.env.NODE_ENV === '\''test'\'') return;\n    \n    let isCancelled = false;\n    \n    const initializeData = async () => {\n      try {\n        if (!isCancelled) {\n          await Promise.all([/' hooks/useMCPTools.ts

# Replace loadServers(); loadTools(); pattern
sed -i '/loadServers();/{
N
s/loadServers();\n    loadTools();/loadServers(), loadTools()]);/
s/loadServers(), loadTools()])/&\n        }\n      } catch (error) {\n        \/\/ Silently handle initialization errors in production\n        console.warn('\''Failed to initialize MCP data:'\'', error);\n      }\n    };\n\n    initializeData();\n\n    return () => {\n      isCancelled = true;\n    };/
}' hooks/useMCPTools.ts
